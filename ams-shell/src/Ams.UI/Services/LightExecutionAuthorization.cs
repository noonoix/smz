namespace Ams.UI.Services;

public enum LightAuthorizationReasonCode
{
    PermitIssued,
    PermitConsumed,
    NotArmed,
    ArmExpired,
    ArmIntentMismatch,
    GateDenied,
    GateReasonMismatch,
    Cancelled,
    Disconnected,
    InvalidTime,
    StaleGateResult,
    ProcessGenerationChanged,
    WatchSessionChanged,
    ProfileChanged,
    PipelineChanged,
    ObservationMissing,
    ObservationAlreadyAuthorized,
    IntentNotAllowed,
    IndependentReasonRequired,
    MalformedRequest,
    PermitUnknown,
    PermitExpired,
    PermitRevoked,
    AlreadyConsumed,
    PermitIntentMismatch,
    ArmRevoked,
}

public sealed record LightArmLease(
    string ArmGenerationId,
    LightExecutionIntent Intent,
    string ProcessGenerationId,
    string WatchSessionId,
    string ProfileRevision,
    string PipelineRevision,
    TimeSpan ArmedAt,
    TimeSpan ExpiresAt);

public sealed record LightAuthorizationRequest(
    LightArmLease ArmLease,
    LightGateResult GateResult,
    LightExecutionIntent Intent,
    string ObservationId,
    string ExpectedProcessGenerationId,
    string ExpectedWatchSessionId,
    string ExpectedProfileRevision,
    string ExpectedPipelineRevision,
    TimeSpan Now,
    TimeSpan MaxGateAge,
    TimeSpan PermitLifetime,
    bool ConnectionHealthy,
    bool CancellationRequested,
    bool IntentAllowed,
    bool IndependentEntryReasonKnown);

/// <summary>Identity only: this permit deliberately contains no command, callback or runtime handle.</summary>
public sealed record LightExecutionPermit(
    string PermitId,
    string ArmGenerationId,
    LightExecutionIntent Intent,
    string ProcessGenerationId,
    string WatchSessionId,
    string ProfileRevision,
    string PipelineRevision,
    string ObservationId,
    TimeSpan IssuedAt,
    TimeSpan ExpiresAt);

public sealed record LightAuthorizationResult(
    bool Succeeded,
    LightAuthorizationReasonCode ReasonCode,
    LightExecutionPermit? Permit = null);

public sealed record LightPermitConsumeContext(
    string PermitId,
    LightExecutionIntent Intent,
    string ProcessGenerationId,
    string WatchSessionId,
    string ProfileRevision,
    string PipelineRevision,
    TimeSpan Now,
    bool ConnectionHealthy,
    bool CancellationRequested);

public sealed record LightPermitConsumeResult(
    bool Succeeded,
    LightAuthorizationReasonCode ReasonCode,
    LightExecutionPermit? Permit = null);

/// <summary>
/// Process-local, fail-closed authorization ledger. It verifies and consumes identities only.
/// It never starts a runtime, invokes a command, writes to a bridge or exposes an execution event.
/// </summary>
public sealed class LightExecutionAuthorizationLedger
{
    private readonly object _sync = new();
    private readonly string _processGenerationId;
    private readonly Func<string> _idFactory;
    private readonly Dictionary<string, PermitEntry> _permits = new(StringComparer.Ordinal);
    private readonly HashSet<string> _authorizedObservations = new(StringComparer.Ordinal);
    private LightArmLease? _activeArm;

    public LightExecutionAuthorizationLedger(
        string processGenerationId,
        Func<string>? idFactory = null)
    {
        if (!ValidId(processGenerationId))
            throw new ArgumentException("Process generation ID is required.", nameof(processGenerationId));
        _processGenerationId = processGenerationId;
        _idFactory = idFactory ?? (() => Guid.NewGuid().ToString("N"));
    }

    public string ProcessGenerationId => _processGenerationId;

    public LightArmLease Arm(
        LightExecutionIntent intent,
        string watchSessionId,
        string profileRevision,
        string pipelineRevision,
        TimeSpan now,
        TimeSpan leaseDuration)
    {
        if (!Enum.IsDefined(intent)) throw new ArgumentOutOfRangeException(nameof(intent));
        if (!ValidId(watchSessionId)) throw new ArgumentException("Watch session ID is required.", nameof(watchSessionId));
        if (!ValidId(profileRevision)) throw new ArgumentException("Profile revision is required.", nameof(profileRevision));
        if (!ValidId(pipelineRevision)) throw new ArgumentException("Pipeline revision is required.", nameof(pipelineRevision));
        if (now < TimeSpan.Zero || leaseDuration <= TimeSpan.Zero)
            throw new ArgumentOutOfRangeException(nameof(leaseDuration));

        lock (_sync)
        {
            RevokeOutstanding(LightAuthorizationReasonCode.ArmRevoked);
            var armId = NextUniqueId();
            _activeArm = new LightArmLease(
                armId, intent, _processGenerationId, watchSessionId, profileRevision,
                pipelineRevision, now, checked(now + leaseDuration));
            return _activeArm;
        }
    }

    public int RevokeAll(LightAuthorizationReasonCode reason = LightAuthorizationReasonCode.PermitRevoked)
    {
        lock (_sync)
        {
            _activeArm = null;
            return RevokeOutstanding(reason);
        }
    }

    public LightAuthorizationResult TryIssue(LightAuthorizationRequest? request)
    {
        lock (_sync)
        {
            LightAuthorizationResult Deny(LightAuthorizationReasonCode reason) => new(false, reason);
            if (request is null || request.ArmLease is null || request.GateResult is null
                || !Enum.IsDefined(request.Intent))
                return Deny(LightAuthorizationReasonCode.MalformedRequest);
            if (request.CancellationRequested)
            {
                _activeArm = null;
                RevokeOutstanding(LightAuthorizationReasonCode.Cancelled);
                return Deny(LightAuthorizationReasonCode.Cancelled);
            }
            if (!request.ConnectionHealthy)
            {
                _activeArm = null;
                RevokeOutstanding(LightAuthorizationReasonCode.Disconnected);
                return Deny(LightAuthorizationReasonCode.Disconnected);
            }
            if (request.Now < TimeSpan.Zero || request.MaxGateAge < TimeSpan.Zero
                || request.PermitLifetime <= TimeSpan.Zero
                || request.GateResult.EvaluatedAt < TimeSpan.Zero
                || request.GateResult.EvaluatedAt > request.Now)
                return Deny(LightAuthorizationReasonCode.InvalidTime);
            if (_activeArm is null)
                return Deny(LightAuthorizationReasonCode.NotArmed);
            if (request.Now >= _activeArm.ExpiresAt)
            {
                _activeArm = null;
                RevokeOutstanding(LightAuthorizationReasonCode.ArmExpired);
                return Deny(LightAuthorizationReasonCode.ArmExpired);
            }
            if (!string.Equals(request.ArmLease.ArmGenerationId, _activeArm.ArmGenerationId, StringComparison.Ordinal))
                return Deny(LightAuthorizationReasonCode.ArmRevoked);
            if (request.Intent != _activeArm.Intent || request.Intent != request.ArmLease.Intent)
                return Deny(LightAuthorizationReasonCode.ArmIntentMismatch);
            if (!Same(request.ExpectedProcessGenerationId, _processGenerationId)
                || !Same(request.ArmLease.ProcessGenerationId, _processGenerationId))
                return Deny(LightAuthorizationReasonCode.ProcessGenerationChanged);
            if (!Same(request.ExpectedWatchSessionId, _activeArm.WatchSessionId)
                || !Same(request.ArmLease.WatchSessionId, _activeArm.WatchSessionId))
                return Deny(LightAuthorizationReasonCode.WatchSessionChanged);
            if (!Same(request.ExpectedProfileRevision, _activeArm.ProfileRevision)
                || !Same(request.ArmLease.ProfileRevision, _activeArm.ProfileRevision))
                return Deny(LightAuthorizationReasonCode.ProfileChanged);
            if (!Same(request.ExpectedPipelineRevision, _activeArm.PipelineRevision)
                || !Same(request.ArmLease.PipelineRevision, _activeArm.PipelineRevision))
                return Deny(LightAuthorizationReasonCode.PipelineChanged);
            if (!request.IntentAllowed)
                return Deny(LightAuthorizationReasonCode.IntentNotAllowed);
            if (request.Intent is LightExecutionIntent.Login or LightExecutionIntent.Disconnect
                && !request.IndependentEntryReasonKnown)
                return Deny(LightAuthorizationReasonCode.IndependentReasonRequired);
            if (request.GateResult.Decision != LightGateDecisionKind.Eligible)
                return Deny(LightAuthorizationReasonCode.GateDenied);
            if (request.GateResult.ReasonCode != LightGateReasonCode.EligibleStableMatch
                || request.GateResult.Intent != request.Intent)
                return Deny(LightAuthorizationReasonCode.GateReasonMismatch);
            if (!Same(request.GateResult.WatchSessionId, request.ExpectedWatchSessionId))
                return Deny(LightAuthorizationReasonCode.WatchSessionChanged);
            if (!Same(request.GateResult.ProfileRevision, request.ExpectedProfileRevision))
                return Deny(LightAuthorizationReasonCode.ProfileChanged);
            if (request.Now - request.GateResult.EvaluatedAt > request.MaxGateAge)
                return Deny(LightAuthorizationReasonCode.StaleGateResult);
            if (!ValidId(request.ObservationId))
                return Deny(LightAuthorizationReasonCode.ObservationMissing);

            var observationKey = string.Join("\u001f",
                _processGenerationId, request.ExpectedWatchSessionId,
                request.ExpectedProfileRevision, request.ObservationId);
            if (_authorizedObservations.Contains(observationKey))
                return Deny(LightAuthorizationReasonCode.ObservationAlreadyAuthorized);

            var expiresAt = Min(checked(request.Now + request.PermitLifetime), _activeArm.ExpiresAt);
            if (expiresAt <= request.Now)
                return Deny(LightAuthorizationReasonCode.PermitExpired);

            var permit = new LightExecutionPermit(
                NextUniqueId(), _activeArm.ArmGenerationId, request.Intent,
                _processGenerationId, _activeArm.WatchSessionId, _activeArm.ProfileRevision,
                _activeArm.PipelineRevision, request.ObservationId, request.Now, expiresAt);
            _authorizedObservations.Add(observationKey);
            _permits.Add(permit.PermitId, new PermitEntry(permit));
            return new LightAuthorizationResult(true, LightAuthorizationReasonCode.PermitIssued, permit);
        }
    }

    public LightPermitConsumeResult TryConsume(LightPermitConsumeContext? context)
    {
        lock (_sync)
        {
            LightPermitConsumeResult Deny(LightAuthorizationReasonCode reason) => new(false, reason);
            if (context is null || !ValidId(context.PermitId) || !Enum.IsDefined(context.Intent))
                return Deny(LightAuthorizationReasonCode.MalformedRequest);
            if (!_permits.TryGetValue(context.PermitId, out var entry))
                return Deny(LightAuthorizationReasonCode.PermitUnknown);
            if (entry.State == PermitState.Consumed)
                return Deny(LightAuthorizationReasonCode.AlreadyConsumed);
            if (entry.State == PermitState.Revoked)
                return Deny(entry.TerminalReason ?? LightAuthorizationReasonCode.PermitRevoked);
            if (entry.State == PermitState.Expired)
                return Deny(LightAuthorizationReasonCode.PermitExpired);
            if (context.CancellationRequested)
            {
                _activeArm = null;
                RevokeOutstanding(LightAuthorizationReasonCode.Cancelled);
                return Deny(LightAuthorizationReasonCode.Cancelled);
            }
            if (!context.ConnectionHealthy)
            {
                _activeArm = null;
                RevokeOutstanding(LightAuthorizationReasonCode.Disconnected);
                return Deny(LightAuthorizationReasonCode.Disconnected);
            }
            if (context.Now < TimeSpan.Zero || context.Now < entry.Permit.IssuedAt)
                return Deny(LightAuthorizationReasonCode.InvalidTime);
            if (context.Now >= entry.Permit.ExpiresAt)
            {
                entry.Expire();
                return Deny(LightAuthorizationReasonCode.PermitExpired);
            }
            if (_activeArm is null || !Same(_activeArm.ArmGenerationId, entry.Permit.ArmGenerationId))
            {
                entry.Revoke(LightAuthorizationReasonCode.ArmRevoked);
                return Deny(LightAuthorizationReasonCode.ArmRevoked);
            }
            if (context.Intent != entry.Permit.Intent)
            {
                entry.Revoke(LightAuthorizationReasonCode.PermitIntentMismatch);
                return Deny(LightAuthorizationReasonCode.PermitIntentMismatch);
            }
            if (!Same(context.ProcessGenerationId, _processGenerationId))
            {
                entry.Revoke(LightAuthorizationReasonCode.ProcessGenerationChanged);
                return Deny(LightAuthorizationReasonCode.ProcessGenerationChanged);
            }
            if (!Same(context.WatchSessionId, entry.Permit.WatchSessionId))
            {
                entry.Revoke(LightAuthorizationReasonCode.WatchSessionChanged);
                return Deny(LightAuthorizationReasonCode.WatchSessionChanged);
            }
            if (!Same(context.ProfileRevision, entry.Permit.ProfileRevision))
            {
                entry.Revoke(LightAuthorizationReasonCode.ProfileChanged);
                return Deny(LightAuthorizationReasonCode.ProfileChanged);
            }
            if (!Same(context.PipelineRevision, entry.Permit.PipelineRevision))
            {
                entry.Revoke(LightAuthorizationReasonCode.PipelineChanged);
                return Deny(LightAuthorizationReasonCode.PipelineChanged);
            }

            entry.Consume();
            return new LightPermitConsumeResult(true,
                LightAuthorizationReasonCode.PermitConsumed, entry.Permit);
        }
    }

    private int RevokeOutstanding(LightAuthorizationReasonCode reason)
    {
        var count = 0;
        foreach (var entry in _permits.Values)
        {
            if (entry.State != PermitState.Issued) continue;
            entry.Revoke(reason);
            count++;
        }
        return count;
    }

    private string NextUniqueId()
    {
        for (var attempt = 0; attempt < 8; attempt++)
        {
            var id = _idFactory();
            if (ValidId(id) && !_permits.ContainsKey(id)
                && !string.Equals(_activeArm?.ArmGenerationId, id, StringComparison.Ordinal))
                return id;
        }
        throw new InvalidOperationException("ID factory did not produce a unique non-empty value.");
    }

    private static bool ValidId(string? value) => !string.IsNullOrWhiteSpace(value);
    private static bool Same(string? left, string? right)
        => ValidId(left) && string.Equals(left, right, StringComparison.Ordinal);
    private static TimeSpan Min(TimeSpan left, TimeSpan right) => left <= right ? left : right;

    private enum PermitState { Issued, Consumed, Revoked, Expired }

    private sealed class PermitEntry
    {
        public PermitEntry(LightExecutionPermit permit) => Permit = permit;
        public LightExecutionPermit Permit { get; }
        public PermitState State { get; private set; } = PermitState.Issued;
        public LightAuthorizationReasonCode? TerminalReason { get; private set; }
        public void Consume() { State = PermitState.Consumed; TerminalReason = LightAuthorizationReasonCode.PermitConsumed; }
        public void Revoke(LightAuthorizationReasonCode reason) { State = PermitState.Revoked; TerminalReason = reason; }
        public void Expire() { State = PermitState.Expired; TerminalReason = LightAuthorizationReasonCode.PermitExpired; }
    }
}
