namespace Ams.UI.Services;

public enum LightAuthorizationDiagnosticState
{
    Disarmed,
    Armed,
    PermitIssued,
    PermitConsumed,
    Denied,
    Revoked,
}

public sealed record LightAuthorizationDiagnosticContext(
    string WatchSessionId,
    string ProfileRevision,
    string PipelineRevision,
    TimeSpan Now,
    bool WatchRunning,
    bool ConnectionHealthy,
    bool CancellationRequested = false);

public sealed record LightAuthorizationDiagnosticSnapshot(
    LightAuthorizationDiagnosticState State,
    LightAuthorizationReasonCode ReasonCode,
    LightExecutionIntent SelectedIntent,
    TimeSpan? ArmExpiresAt = null,
    string? PermitId = null,
    TimeSpan? PermitExpiresAt = null)
{
    public bool IsArmed => State is LightAuthorizationDiagnosticState.Armed
        or LightAuthorizationDiagnosticState.PermitIssued;
}

/// <summary>
/// Manual authorization simulator. Arm, issue and consume are separate explicit method calls.
/// Consume only updates the ledger and never invokes an action, bridge, callback or runtime.
/// </summary>
public sealed class NonExecutingLightAuthorizationDiagnostics
{
    private static readonly LightExecutionIntent[] Allowed =
    {
        LightExecutionIntent.Desktop,
        LightExecutionIntent.CharacterDashboard,
        LightExecutionIntent.EnteringGameLoading,
        LightExecutionIntent.Game,
        LightExecutionIntent.Targeted,
    };

    private readonly LightExecutionAuthorizationLedger _ledger;
    private readonly TimeSpan _armLifetime;
    private readonly TimeSpan _permitLifetime;
    private readonly TimeSpan _maxGateAge;
    private LightArmLease? _arm;
    private LightExecutionPermit? _permit;
    private LightExecutionIntent _selectedIntent = LightExecutionIntent.Desktop;

    public NonExecutingLightAuthorizationDiagnostics(
        string processGenerationId,
        TimeSpan? armLifetime = null,
        TimeSpan? permitLifetime = null,
        TimeSpan? maxGateAge = null,
        Func<string>? idFactory = null)
    {
        _armLifetime = armLifetime ?? TimeSpan.FromSeconds(10);
        _permitLifetime = permitLifetime ?? TimeSpan.FromSeconds(2);
        _maxGateAge = maxGateAge ?? TimeSpan.FromMilliseconds(500);
        if (_armLifetime <= TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(armLifetime));
        if (_permitLifetime <= TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(permitLifetime));
        if (_maxGateAge < TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(maxGateAge));
        _ledger = new LightExecutionAuthorizationLedger(processGenerationId, idFactory);
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Disarmed,
            LightAuthorizationReasonCode.NotArmed);
    }

    public static IReadOnlyList<LightExecutionIntent> AllowedIntents => Allowed;
    public string ProcessGenerationId => _ledger.ProcessGenerationId;
    public LightExecutionIntent SelectedIntent => _selectedIntent;
    public LightAuthorizationDiagnosticSnapshot Snapshot { get; private set; }
    public LightExecutionPermit? CurrentPermit => _permit;
    public bool CanIssue => Snapshot.State == LightAuthorizationDiagnosticState.Armed;
    public bool CanConsume => Snapshot.State == LightAuthorizationDiagnosticState.PermitIssued;

    public LightAuthorizationDiagnosticSnapshot SelectIntent(LightExecutionIntent intent)
    {
        if (!Allowed.Contains(intent))
        {
            RevokeInternal(LightAuthorizationReasonCode.IntentNotAllowed);
            Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Denied,
                LightAuthorizationReasonCode.IntentNotAllowed);
            return Snapshot;
        }
        if (intent == _selectedIntent) return Snapshot;
        RevokeInternal(LightAuthorizationReasonCode.ArmIntentMismatch);
        _selectedIntent = intent;
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Disarmed,
            LightAuthorizationReasonCode.NotArmed);
        return Snapshot;
    }

    public LightAuthorizationDiagnosticSnapshot Arm(LightAuthorizationDiagnosticContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        if (!context.WatchRunning || !context.ConnectionHealthy)
            return RevokeAndDeny(LightAuthorizationReasonCode.Disconnected);
        if (context.CancellationRequested)
            return RevokeAndDeny(LightAuthorizationReasonCode.Cancelled);
        if (!Valid(context.WatchSessionId) || !Valid(context.ProfileRevision)
            || !Valid(context.PipelineRevision) || context.Now < TimeSpan.Zero)
            return RevokeAndDeny(LightAuthorizationReasonCode.MalformedRequest);

        _ledger.RevokeAll(LightAuthorizationReasonCode.ArmRevoked);
        _permit = null;
        _arm = _ledger.Arm(_selectedIntent, context.WatchSessionId,
            context.ProfileRevision, context.PipelineRevision, context.Now, _armLifetime);
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Armed,
            LightAuthorizationReasonCode.NotArmed, _arm.ExpiresAt);
        return Snapshot;
    }

    public LightAuthorizationDiagnosticSnapshot Issue(
        LightAuthorizationDiagnosticContext context,
        LightGateResult gateResult,
        string observationId)
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(gateResult);
        if (_arm is null || Snapshot.State != LightAuthorizationDiagnosticState.Armed)
        {
            Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Denied,
                LightAuthorizationReasonCode.NotArmed, _arm?.ExpiresAt);
            return Snapshot;
        }

        var result = _ledger.TryIssue(new LightAuthorizationRequest(
            _arm, gateResult, _selectedIntent, observationId,
            _ledger.ProcessGenerationId, context.WatchSessionId, context.ProfileRevision,
            context.PipelineRevision, context.Now, _maxGateAge, _permitLifetime,
            context.WatchRunning && context.ConnectionHealthy,
            context.CancellationRequested,
            Allowed.Contains(_selectedIntent),
            IndependentEntryReasonKnown: false));
        if (!result.Succeeded || result.Permit is null)
        {
            var armExpiresAt = _arm?.ExpiresAt;
            if (InvalidatesArm(result.ReasonCode))
                RevokeInternal(result.ReasonCode);
            Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Denied,
                result.ReasonCode, armExpiresAt);
            return Snapshot;
        }

        _permit = result.Permit;
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.PermitIssued,
            result.ReasonCode, _arm.ExpiresAt, _permit);
        return Snapshot;
    }

    public LightAuthorizationDiagnosticSnapshot Consume(LightAuthorizationDiagnosticContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        if (_permit is null)
        {
            Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Denied,
                LightAuthorizationReasonCode.PermitUnknown, _arm?.ExpiresAt);
            return Snapshot;
        }
        var result = _ledger.TryConsume(new LightPermitConsumeContext(
            _permit.PermitId, _selectedIntent, _ledger.ProcessGenerationId,
            context.WatchSessionId, context.ProfileRevision, context.PipelineRevision,
            context.Now, context.WatchRunning && context.ConnectionHealthy,
            context.CancellationRequested));
        var permit = _permit;
        var armExpiresAt = _arm?.ExpiresAt;
        if (!result.Succeeded && InvalidatesArm(result.ReasonCode))
            RevokeInternal(result.ReasonCode);
        Snapshot = result.Succeeded
            ? NewSnapshot(LightAuthorizationDiagnosticState.PermitConsumed,
                result.ReasonCode, armExpiresAt, result.Permit)
            : NewSnapshot(LightAuthorizationDiagnosticState.Denied,
                result.ReasonCode, armExpiresAt, permit);
        return Snapshot;
    }

    public LightAuthorizationDiagnosticSnapshot Revoke(
        LightAuthorizationReasonCode reason = LightAuthorizationReasonCode.PermitRevoked)
    {
        RevokeInternal(reason);
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Revoked, reason);
        return Snapshot;
    }

    private LightAuthorizationDiagnosticSnapshot RevokeAndDeny(LightAuthorizationReasonCode reason)
    {
        RevokeInternal(reason);
        Snapshot = NewSnapshot(LightAuthorizationDiagnosticState.Denied, reason);
        return Snapshot;
    }

    private void RevokeInternal(LightAuthorizationReasonCode reason)
    {
        _ledger.RevokeAll(reason);
        _arm = null;
        _permit = null;
    }

    private static bool InvalidatesArm(LightAuthorizationReasonCode reason)
        => reason is LightAuthorizationReasonCode.ArmExpired
            or LightAuthorizationReasonCode.Cancelled
            or LightAuthorizationReasonCode.Disconnected
            or LightAuthorizationReasonCode.ProcessGenerationChanged
            or LightAuthorizationReasonCode.WatchSessionChanged
            or LightAuthorizationReasonCode.ProfileChanged
            or LightAuthorizationReasonCode.PipelineChanged
            or LightAuthorizationReasonCode.ArmRevoked
            or LightAuthorizationReasonCode.PermitIntentMismatch;

    private LightAuthorizationDiagnosticSnapshot NewSnapshot(
        LightAuthorizationDiagnosticState state,
        LightAuthorizationReasonCode reason,
        TimeSpan? armExpiresAt = null,
        LightExecutionPermit? permit = null)
        => new(state, reason, _selectedIntent, armExpiresAt,
            permit?.PermitId, permit?.ExpiresAt);

    private static bool Valid(string? value) => !string.IsNullOrWhiteSpace(value);
}
