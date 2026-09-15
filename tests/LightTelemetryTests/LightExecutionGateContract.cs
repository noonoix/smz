using System.Reflection;
using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class LightExecutionGateContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = Run();
        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Light execution gate results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Light execution gate contract failed: {failed}");
    }

    private static IReadOnlyList<(bool Passed, string Name)> Run()
    {
        var checks = new List<(bool, string)>();
        void Check(bool condition, string name) => checks.Add((condition, name));

        var profile = new LightStateProfile
        {
            Id = "game", Name = "Game", LuxCenter = 26.7, LuxTolerance = 1,
            StableDurationMs = 1250, HysteresisLux = 1,
        };
        var stable = new LightStateClassification(
            LightStateClassificationKind.Stable, 26.7, profile, 1);
        var now = TimeSpan.FromSeconds(10);

        LightGateInput Valid(
            LightStateClassification? classification = null,
            LightExecutionIntent intent = LightExecutionIntent.Game)
            => new(
                intent,
                classification ?? stable,
                ObservedAt: now - TimeSpan.FromMilliseconds(100),
                StableSince: now - TimeSpan.FromMilliseconds(1250),
                Now: now,
                WatchSessionId: "watch-2",
                ExpectedWatchSessionId: "watch-2",
                ProfileRevision: "profiles-b",
                ExpectedProfileRevision: "profiles-b",
                ConnectionHealthy: true,
                CancellationRequested: false,
                MaxSampleAge: TimeSpan.FromSeconds(2),
                RequiredStableDuration: TimeSpan.FromMilliseconds(1250));

        var eligible = LightExecutionGate.Evaluate(Valid());
        Check(eligible.IsEligible
              && eligible.ReasonCode == LightGateReasonCode.EligibleStableMatch
              && eligible.SampleAge == TimeSpan.FromMilliseconds(100)
              && eligible.StableDuration == TimeSpan.FromMilliseconds(1250),
            "fresh stable intent match is diagnostically eligible");

        Check(LightExecutionGate.Evaluate(Valid() with { CancellationRequested = true }).ReasonCode
              == LightGateReasonCode.Cancelled,
            "cancellation fails closed with highest precedence");
        Check(LightExecutionGate.Evaluate(Valid() with { ConnectionHealthy = false }).ReasonCode
              == LightGateReasonCode.Disconnected,
            "disconnect fails closed");
        Check(LightExecutionGate.Evaluate(Valid() with { WatchSessionId = "watch-1" }).ReasonCode
              == LightGateReasonCode.WatchSessionChanged,
            "observation from an old Watch session is denied");
        Check(LightExecutionGate.Evaluate(Valid() with { ObservedAt = now + TimeSpan.FromTicks(1) }).ReasonCode
              == LightGateReasonCode.InvalidTime,
            "impossible monotonic ordering is denied");
        Check(LightExecutionGate.Evaluate(Valid() with {
                ObservedAt = now - TimeSpan.FromMilliseconds(2001),
                StableSince = now - TimeSpan.FromSeconds(3) }).ReasonCode
              == LightGateReasonCode.StaleSample,
            "sample one millisecond beyond the age limit is denied");
        Check(LightExecutionGate.Evaluate(Valid() with {
                ObservedAt = now - TimeSpan.FromSeconds(2),
                StableSince = now - TimeSpan.FromSeconds(3) }).IsEligible,
            "sample exactly at the age limit is accepted");
        Check(LightExecutionGate.Evaluate(Valid() with { ProfileRevision = "profiles-a" }).ReasonCode
              == LightGateReasonCode.ProfileChanged,
            "profile mutation invalidates prior observations");

        LightStateClassification Kind(LightStateClassificationKind kind)
            => new(kind, 26.7, kind is LightStateClassificationKind.Candidate or LightStateClassificationKind.Stable
                ? profile : null);
        Check(LightExecutionGate.Evaluate(Valid(Kind(LightStateClassificationKind.Unknown))).ReasonCode
              == LightGateReasonCode.UnknownState, "Unknown is denied");
        Check(LightExecutionGate.Evaluate(Valid(Kind(LightStateClassificationKind.Invalid))).ReasonCode
              == LightGateReasonCode.InvalidState, "Invalid is denied");
        Check(LightExecutionGate.Evaluate(Valid(Kind(LightStateClassificationKind.Ambiguous))).ReasonCode
              == LightGateReasonCode.AmbiguousState, "Ambiguous is denied");
        Check(LightExecutionGate.Evaluate(Valid(Kind(LightStateClassificationKind.Candidate))).ReasonCode
              == LightGateReasonCode.CandidateOnly, "Candidate is denied");
        Check(LightExecutionGate.Evaluate(Valid(Kind((LightStateClassificationKind)999))).ReasonCode
              == LightGateReasonCode.UnsupportedState, "future classifier kinds fail closed");

        Check(LightExecutionGate.Evaluate(Valid() with {
                StableSince = now - TimeSpan.FromMilliseconds(1249) }).ReasonCode
              == LightGateReasonCode.NotStableLongEnough,
            "stability one millisecond below the requirement is denied");
        Check(LightExecutionGate.Evaluate(Valid(intent: LightExecutionIntent.Desktop)).ReasonCode
              == LightGateReasonCode.IntentMismatch,
            "stable state for another intent is denied");

        var loginProfile = new LightStateProfile { Id = "login-or-dc", Name = "Login/DC" };
        var loginStable = new LightStateClassification(
            LightStateClassificationKind.Stable, 5.8, loginProfile, 1);
        Check(LightExecutionGate.Evaluate(Valid(loginStable, LightExecutionIntent.Login)).IsEligible,
            "Login maps to the shared Login/DC profile");
        Check(LightExecutionGate.Evaluate(Valid(loginStable, LightExecutionIntent.Disconnect)).IsEligible,
            "Disconnect maps diagnostically to Login/DC without executing ESC");

        // Module initializers must not start parallel workers: workers can wait for module
        // initialization and deadlock the test host. Repeated equality plus the evaluator's
        // lack of mutable fields proves deterministic re-entrancy here; runtime concurrency
        // belongs in a normal test method after module initialization.
        var repeated = Enumerable.Range(0, 100)
            .Select(_ => LightExecutionGate.Evaluate(Valid()))
            .ToArray();
        Check(repeated.All(x => x == eligible),
            "repeated evaluation is deterministic and stateless");

        var resultProperties = typeof(LightGateResult).GetProperties(BindingFlags.Public | BindingFlags.Instance);
        Check(resultProperties.All(x => !typeof(Delegate).IsAssignableFrom(x.PropertyType))
              && typeof(LightExecutionGate).GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
                  .All(x => x.IsLiteral),
            "gate result has no executable callback and evaluator stores no mutable state");

        return checks;
    }
}
