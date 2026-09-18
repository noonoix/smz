using System;
using Ams.UI.Models;

namespace Ams.UI.Services;

public sealed record SessionCycleTransition(bool Accepted, string Reason, SessionCycleState State);

/// <summary>
/// Pure session coordinator for the long-running five-cycle workflow.
/// It authorizes state changes only; it never launches processes, sends HID input,
/// changes Boot Loader settings, or invokes RunEngine. Those actions remain explicit
/// caller responsibilities and can be added behind a separately tested executor.
/// </summary>
public sealed class SessionCycleOrchestrator
{
    private readonly object _gate = new();
    private SessionCycleState _state;

    public SessionCycleOrchestrator(int maximumCycles = 5)
        => _state = SessionCycleState.Initial(maximumCycles);

    public SessionCycleState State { get { lock (_gate) return _state; } }
    public event EventHandler<SessionCycleState>? StateChanged;

    public SessionCycleTransition Start()
        => Mutate("session started", current =>
        {
            if (current.Running) return Reject(current, "session already running");
            return Accept(current with
            {
                CycleNumber = 1,
                Phase = SessionCyclePhase.Desktop,
                Running = true,
                SessionStartedAtUtc = DateTimeOffset.UtcNow,
            }, "session started at Desktop");
        });

    /// <summary>Idempotent once-per-session gate. The actual Windows command is not executed here.</summary>
    public SessionCycleTransition MarkBootLoaderConfigured()
        => Mutate("boot loader configured", current =>
        {
            if (!current.Running) return Reject(current, "session is not running");
            if (current.BootLoaderConfigured) return Reject(current, "boot loader already configured for this session");
            return Accept(current with { BootLoaderConfigured = true }, "boot loader configuration authorized once");
        });

    /// <summary>Reports a fresh stable Guard profile. Duplicate observations are denied.</summary>
    public SessionCycleTransition ObserveProfile(string profileId)
        => Mutate("profile observed", current =>
        {
            if (!current.Running) return Reject(current, "session is not running");
            if (string.IsNullOrWhiteSpace(profileId)) return Reject(current, "profile is empty");

            return profileId switch
            {
                "desktop" => AcceptProfile(current, SessionCyclePhase.Desktop, "Desktop observed"),
                "login-or-dc" => AcceptLoginOrDc(current),
                "character-dashboard" => AcceptExpected(current, SessionCyclePhase.LoginOrDc, SessionCyclePhase.CharacterDashboard, "Character Dashboard observed"),
                "entering-game-loading" => AcceptExpected(current, SessionCyclePhase.CharacterDashboard, SessionCyclePhase.EnteringGameLoading, "Entering Game/Loading observed"),
                "game" => AcceptGame(current),
                "targeted" => AcceptExpected(current, SessionCyclePhase.Game, SessionCyclePhase.Targeted, "Targeted side-state observed"),
                _ => Reject(current, "unknown profile: " + profileId),
            };
        });

    public SessionCycleTransition StartResumable()
        => Mutate("resumable route requested", current =>
        {
            if (!current.Running) return Reject(current, "session is not running");
            if (current.Phase != SessionCyclePhase.Game) return Reject(current, "Resumable is only valid after Game");
            return Accept(current with { Phase = SessionCyclePhase.Resumable }, "Resumable route authorized");
        });

    public SessionCycleTransition CompleteResumable()
        => Mutate("resumable route completed", current =>
        {
            if (current.Phase != SessionCyclePhase.Resumable) return Reject(current, "Resumable is not active");
            return Accept(current with { Phase = SessionCyclePhase.Game }, "returned to Game after Resumable");
        });

    /// <summary>Authorize the end-of-window restart. The caller performs Win+X/restart.</summary>
    public SessionCycleTransition RequestRestart()
        => Mutate("restart requested", current =>
        {
            if (!current.Running) return Reject(current, "session is not running");
            if (current.Phase != SessionCyclePhase.Game) return Reject(current, "restart is only valid from Game");
            if (current.CycleNumber >= current.MaximumCycles)
                return Accept(current with { Phase = SessionCyclePhase.Completed, Running = false }, "fifth cycle completed; safe stop");
            return Accept(current with { Phase = SessionCyclePhase.RestartPending }, "restart authorized");
        });

    public SessionCycleTransition MarkRestartIssued()
        => Mutate("restart issued", current =>
        {
            if (current.Phase != SessionCyclePhase.RestartPending) return Reject(current, "restart is not pending");
            return Accept(current with { Phase = SessionCyclePhase.AwaitingReboot, RebootCount = current.RebootCount + 1 }, "awaiting reboot");
        });

    /// <summary>Desktop after reboot resumes the next cycle without reconfiguring Boot Loader.</summary>
    public SessionCycleTransition ObserveRebootedDesktop()
        => Mutate("desktop observed after reboot", current =>
        {
            if (current.Phase != SessionCyclePhase.AwaitingReboot) return Reject(current, "reboot was not pending");
            return Accept(current with { CycleNumber = current.CycleNumber + 1, Phase = SessionCyclePhase.Desktop }, "next cycle started; boot loader configuration retained");
        });

    public SessionCycleTransition Stop(string reason = "stopped by operator")
        => Mutate(reason, current => Accept(current with { Phase = SessionCyclePhase.Idle, Running = false, LastReason = reason }, reason));

    public SessionCycleTransition Fault(string reason)
        => Mutate(reason, current => Accept(current with { Phase = SessionCyclePhase.Faulted, Running = false, LastReason = reason }, reason));

    private SessionCycleTransition AcceptProfile(SessionCycleState current, SessionCyclePhase phase, string reason)
        => current.Phase switch
        {
            SessionCyclePhase.Desktop when phase == SessionCyclePhase.Desktop => Reject(current, "duplicate Desktop observation"),
            SessionCyclePhase.AwaitingReboot when phase == SessionCyclePhase.Desktop => Accept(current with { CycleNumber = current.CycleNumber + 1, Phase = phase }, reason),
            _ => Accept(current with { Phase = phase }, reason),
        };

    private SessionCycleTransition AcceptLoginOrDc(SessionCycleState current)
    {
        if (current.Phase is SessionCyclePhase.Game or SessionCyclePhase.Targeted or SessionCyclePhase.Resumable)
            return Accept(current with { Phase = SessionCyclePhase.LoginOrDc }, "DC detected; Login/DC recovery authorized");
        return AcceptExpected(current, SessionCyclePhase.Desktop, SessionCyclePhase.LoginOrDc, "Login/DC observed");
    }

    private SessionCycleTransition AcceptGame(SessionCycleState current)
    {
        if (current.Phase == SessionCyclePhase.Targeted)
            return Accept(current with { Phase = SessionCyclePhase.Game }, "returned from Targeted to Game");
        return AcceptExpected(current, SessionCyclePhase.EnteringGameLoading, SessionCyclePhase.Game, "Game observed");
    }

    private static SessionCycleTransition AcceptExpected(SessionCycleState current, SessionCyclePhase expected, SessionCyclePhase next, string reason)
        => current.Phase == expected
            ? Accept(current with { Phase = next }, reason)
            : Reject(current, $"unexpected phase: expected {expected}, actual {current.Phase}");

    private SessionCycleTransition Mutate(string reason, Func<SessionCycleState, SessionCycleTransition> operation)
    {
        SessionCycleState next;
        SessionCycleTransition result;
        lock (_gate)
        {
            result = operation(_state);
            next = result.State;
            if (result.Accepted)
            {
                var now = DateTimeOffset.UtcNow;
                next = next with { LastTransitionAtUtc = now, LastReason = reason };
                result = result with { State = next };
                _state = next;
            }
        }
        if (result.Accepted) StateChanged?.Invoke(this, result.State);
        return result;
    }

    private static SessionCycleTransition Accept(SessionCycleState state, string reason)
        => new(true, reason, state);

    private static SessionCycleTransition Reject(SessionCycleState state, string reason)
        => new(false, reason, state);
}
