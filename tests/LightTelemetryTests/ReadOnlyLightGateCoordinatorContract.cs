using System.Reflection;
using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class ReadOnlyLightGateCoordinatorContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = Run();
        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Read-only light gate coordinator results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Read-only light gate coordinator contract failed: {failed}");
    }

    private static IReadOnlyList<(bool Passed, string Name)> Run()
    {
        var checks = new List<(bool, string)>();
        void Check(bool condition, string name) => checks.Add((condition, name));

        var profiles = new[]
        {
            new LightStateProfile
            {
                Id = "game", Name = "Game", Enabled = true, LuxCenter = 26.7,
                LuxTolerance = 1, StableDurationMs = 1250, HysteresisLux = 1,
            },
            new LightStateProfile
            {
                Id = "login-or-dc", Name = "Login/DC", Enabled = true, LuxCenter = 5.8,
                LuxTolerance = 2.6, StableDurationMs = 1250, HysteresisLux = 1,
            },
        };
        var revision = ReadOnlyLightGateCoordinator.ComputeProfileRevision(profiles);
        Check(revision == ReadOnlyLightGateCoordinator.ComputeProfileRevision(profiles.Reverse()),
            "profile revision is deterministic and independent of collection order");
        var changedProfiles = profiles.Select(x => new LightStateProfile
        {
            Id = x.Id, Name = x.Name, Enabled = x.Enabled,
            LuxCenter = x.Id == "game" ? x.LuxCenter + 0.1 : x.LuxCenter,
            LuxTolerance = x.LuxTolerance, StableDurationMs = x.StableDurationMs,
            HysteresisLux = x.HysteresisLux,
        }).ToArray();
        Check(revision != ReadOnlyLightGateCoordinator.ComputeProfileRevision(changedProfiles),
            "profile revision changes when calibration changes");

        var ids = new Queue<string>(new[] { "session-1", "session-2" });
        var coordinator = new ReadOnlyLightGateCoordinator(
            TimeSpan.FromSeconds(2), () => ids.Dequeue());
        var t0 = TimeSpan.FromSeconds(10);
        var session1 = coordinator.StartSession(profiles, t0);
        Check(session1 == "session-1" && coordinator.IsSessionActive
              && coordinator.LastResult.ReasonCode == LightGateReasonCode.UnknownState,
            "Watch start creates a diagnostic session in denied state");

        var game = profiles[0];
        var candidate = new LightStateClassification(
            LightStateClassificationKind.Candidate, 26.7, game, 1);
        var stable = new LightStateClassification(
            LightStateClassificationKind.Stable, 26.7, game, 1);
        var candidateResult = coordinator.Observe(
            LightExecutionIntent.Game, candidate, t0, t0, session1, revision);
        Check(candidateResult.ReasonCode == LightGateReasonCode.CandidateOnly,
            "candidate observation remains denied");
        var earlyStable = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0 + TimeSpan.FromMilliseconds(1249),
            t0 + TimeSpan.FromMilliseconds(1249), session1, revision);
        Check(earlyStable.ReasonCode == LightGateReasonCode.NotStableLongEnough,
            "coordinator preserves candidate timing and denies early stability");
        var eligible = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0 + TimeSpan.FromMilliseconds(1250),
            t0 + TimeSpan.FromMilliseconds(1250), session1, revision);
        Check(eligible.IsEligible && eligible.StableDuration == TimeSpan.FromMilliseconds(1250),
            "coordinator becomes diagnostically eligible at the exact stability boundary");

        var session2 = coordinator.StartSession(profiles, t0 + TimeSpan.FromSeconds(2));
        var oldSession = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0 + TimeSpan.FromSeconds(2),
            t0 + TimeSpan.FromSeconds(2), session1, revision);
        Check(session2 == "session-2" && oldSession.ReasonCode == LightGateReasonCode.WatchSessionChanged,
            "reconnect rejects observations from the previous session");

        var newRevision = coordinator.RefreshProfiles(changedProfiles, t0 + TimeSpan.FromSeconds(3));
        var oldRevision = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0 + TimeSpan.FromSeconds(3),
            t0 + TimeSpan.FromSeconds(3), session2, revision);
        Check(newRevision != revision && oldRevision.ReasonCode == LightGateReasonCode.ProfileChanged,
            "profile Save invalidates classifications made with the previous revision");

        var stale = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0, t0 + TimeSpan.FromSeconds(3),
            session2, newRevision);
        Check(stale.ReasonCode == LightGateReasonCode.StaleSample,
            "stale observation is denied by the coordinator path");

        var stopped = coordinator.Stop(t0 + TimeSpan.FromSeconds(4));
        Check(!coordinator.IsSessionActive && stopped.ReasonCode == LightGateReasonCode.Disconnected,
            "Watch stop immediately invalidates the diagnostic session");
        var afterStop = coordinator.Observe(
            LightExecutionIntent.Game, stable, t0 + TimeSpan.FromSeconds(4),
            t0 + TimeSpan.FromSeconds(4), session2, newRevision);
        Check(afterStop.ReasonCode == LightGateReasonCode.Disconnected,
            "observations after Stop remain fail-closed");

        var fields = typeof(ReadOnlyLightGateCoordinator)
            .GetFields(BindingFlags.Instance | BindingFlags.NonPublic);
        Check(fields.All(field => !typeof(IBoardBridge).IsAssignableFrom(field.FieldType)
                                  && !typeof(Delegate).IsAssignableFrom(field.FieldType)
                                      || field.Name == "_sessionIdFactory"),
            "coordinator stores no bridge or actuator dependency");
        Check(typeof(ReadOnlyLightGateCoordinator).GetEvents().Length == 0,
            "coordinator exposes no event callback capable of triggering execution");

        return checks;
    }
}
