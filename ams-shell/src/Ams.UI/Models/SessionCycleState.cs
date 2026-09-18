using System;

namespace Ams.UI.Models;

public enum SessionCyclePhase
{
    Idle,
    Desktop,
    LoginOrDc,
    CharacterDashboard,
    EnteringGameLoading,
    Game,
    Targeted,
    Resumable,
    RestartPending,
    AwaitingReboot,
    Completed,
    Faulted,
}

/// <summary>Durable, UI-independent state for the five-cycle Guard session.</summary>
public sealed record SessionCycleState(
    int CycleNumber,
    int MaximumCycles,
    SessionCyclePhase Phase,
    bool BootLoaderConfigured,
    int RebootCount,
    DateTimeOffset SessionStartedAtUtc,
    DateTimeOffset LastTransitionAtUtc,
    string LastReason,
    bool Running)
{
    public static SessionCycleState Initial(int maximumCycles = 5)
    {
        if (maximumCycles < 1) throw new ArgumentOutOfRangeException(nameof(maximumCycles));
        var now = DateTimeOffset.UtcNow;
        return new(0, maximumCycles, SessionCyclePhase.Idle, false, 0, now, now, "not started", false);
    }
}
