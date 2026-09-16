using Ams.UI.Models;

namespace Ams.UI.Services;

public enum LightGuardEntryContext
{
    None,
    Login,
    Disconnect,
    Targeted,
}

public sealed record LightGuardTransitionInput(
    string ProfileId,
    string ProfileRevision,
    string ExpectedProfileRevision,
    string PipelineRevision,
    string ExpectedPipelineRevision,
    bool ObservationEnabled,
    bool CalibrationSynchronized,
    bool ConnectionHealthy);

public sealed record LightGuardTransitionDecision(
    bool ShouldExecute,
    PipelineKind? Pipeline,
    LightExecutionIntent? Intent,
    LightGuardEntryContext Context,
    int? CurrentStage,
    int? NextStage,
    string Reason)
{
    public static LightGuardTransitionDecision Denied(string reason, int? stage = null)
        => new(false, null, null, LightGuardEntryContext.None, stage, stage, reason);
}

/// <summary>
/// Fail-closed, one-shot transition planner for the Phase 7 Guard state machine.
/// It selects a visible pipeline tab but deliberately does not invoke RunEngine. The caller
/// must validate the returned pipeline revision again immediately before execution.
/// </summary>
public sealed class LightGuardTransitionController
{
    private int? _stage;
    private string? _lastStableProfile;
    private bool _targetedActive;

    public int? CurrentStage => _stage;
    public bool TargetedActive => _targetedActive;

    /// <summary>Clears the one-shot latch after the optical state becomes unknown.</summary>
    public void ObserveUnknown() => _lastStableProfile = null;

    /// <summary>Stop or Guard OFF returns the planner to its initial state.</summary>
    public void Reset()
    {
        _stage = null;
        _lastStableProfile = null;
        _targetedActive = false;
    }

    public LightGuardTransitionDecision ObserveStable(LightGuardTransitionInput input)
    {
        ArgumentNullException.ThrowIfNull(input);

        if (!input.ConnectionHealthy)
            return LightGuardTransitionDecision.Denied("connection unhealthy", _stage);
        if (!input.ObservationEnabled)
            return LightGuardTransitionDecision.Denied("Guard observation is disabled", _stage);
        if (!input.CalibrationSynchronized)
            return LightGuardTransitionDecision.Denied("Guard calibration is not synchronized", _stage);
        if (string.IsNullOrWhiteSpace(input.ProfileRevision)
            || !string.Equals(input.ProfileRevision, input.ExpectedProfileRevision, StringComparison.Ordinal))
            return LightGuardTransitionDecision.Denied("calibration revision mismatch", _stage);
        if (string.IsNullOrWhiteSpace(input.PipelineRevision)
            || !string.Equals(input.PipelineRevision, input.ExpectedPipelineRevision, StringComparison.Ordinal))
            return LightGuardTransitionDecision.Denied("pipeline revision mismatch", _stage);
        if (!LightGuardCalibrationProtocol.ProfileIds.Contains(input.ProfileId, StringComparer.Ordinal))
            return LightGuardTransitionDecision.Denied("unknown Guard profile", _stage);

        // Guard firmware can report the same stable state repeatedly. A state change (or an
        // unknown event) is required before the same profile can authorize another transition.
        if (string.Equals(_lastStableProfile, input.ProfileId, StringComparison.Ordinal))
            return LightGuardTransitionDecision.Denied("duplicate stable state", _stage);
        _lastStableProfile = input.ProfileId;

        return input.ProfileId switch
        {
            "desktop" => PlanDesktop(),
            "login-or-dc" => PlanLoginOrDisconnect(),
            "character-dashboard" => PlanLinear(
                expectedStage: 2,
                nextStage: 3,
                PipelineKind.CharacterDashboard,
                LightExecutionIntent.CharacterDashboard,
                LightGuardEntryContext.None,
                "stage 2 -> stage 3"),
            "entering-game-loading" => PlanLinear(
                expectedStage: 3,
                nextStage: 4,
                PipelineKind.EnteringGameLoading,
                LightExecutionIntent.EnteringGameLoading,
                LightGuardEntryContext.None,
                "stage 3 -> stage 4"),
            "game" => PlanGame(),
            "targeted" => PlanTargeted(),
            _ => LightGuardTransitionDecision.Denied("unsupported Guard profile", _stage),
        };
    }

    private LightGuardTransitionDecision PlanDesktop()
    {
        if (_stage is not null)
            return LightGuardTransitionDecision.Denied("desktop is only valid as the initial stage", _stage);
        _stage = 1;
        return Execute(PipelineKind.Desktop, LightExecutionIntent.Desktop,
            LightGuardEntryContext.None, null, 1, "initial stage 1");
    }

    private LightGuardTransitionDecision PlanLoginOrDisconnect()
    {
        if (_targetedActive || _stage is >= 3 and <= 5)
        {
            _targetedActive = false;
            _stage = 2;
            return Execute(PipelineKind.LoginOrDc, LightExecutionIntent.Disconnect,
                LightGuardEntryContext.Disconnect, 2, 2,
                "DC fallback to stage 2; resume ordered progression");
        }
        if (_stage == 1)
        {
            _stage = 2;
            return Execute(PipelineKind.LoginOrDc, LightExecutionIntent.Login,
                LightGuardEntryContext.Login, 2, 2, "stage 1 -> stage 2");
        }
        return LightGuardTransitionDecision.Denied("Login / DC is not the expected next state", _stage);
    }

    private LightGuardTransitionDecision PlanGame()
    {
        if (_targetedActive)
        {
            _targetedActive = false;
            return new LightGuardTransitionDecision(
                ShouldExecute: false,
                Pipeline: PipelineKind.Game,
                Intent: LightExecutionIntent.Game,
                Context: LightGuardEntryContext.None,
                CurrentStage: 5,
                NextStage: 5,
                Reason: "Targeted side-state returned to Game; no Game Steps replayed");
        }
        if (_stage != 4)
            return LightGuardTransitionDecision.Denied("Game is not the expected next state", _stage);
        _stage = 5;
        return Execute(PipelineKind.Game, LightExecutionIntent.Game,
            LightGuardEntryContext.None, 5, 5, "stage 4 -> stage 5");
    }

    private LightGuardTransitionDecision PlanTargeted()
    {
        if (_stage != 5 || _targetedActive)
            return LightGuardTransitionDecision.Denied("Targeted is only a side-state from Game", _stage);
        _targetedActive = true;
        return Execute(PipelineKind.Targeted, LightExecutionIntent.Targeted,
            LightGuardEntryContext.Targeted, 5, 5,
            "Game -> Targeted side-state; return to Game after fresh stable match");
    }

    private LightGuardTransitionDecision PlanLinear(
        int expectedStage,
        int nextStage,
        PipelineKind pipeline,
        LightExecutionIntent intent,
        LightGuardEntryContext context,
        string reason)
    {
        if (_stage != expectedStage)
            return LightGuardTransitionDecision.Denied("unexpected ordered stage", _stage);
        _stage = nextStage;
        return Execute(pipeline, intent, context, nextStage, nextStage, reason);
    }

    private LightGuardTransitionDecision Execute(
        PipelineKind pipeline,
        LightExecutionIntent intent,
        LightGuardEntryContext context,
        int? currentStage,
        int? nextStage,
        string reason)
        => new(true, pipeline, intent, context, currentStage, nextStage, reason);
}
