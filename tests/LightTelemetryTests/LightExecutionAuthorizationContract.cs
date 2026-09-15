using System.Reflection;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

internal static class LightExecutionAuthorizationContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = Run();
        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Light authorization results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Light authorization contract failed: {failed}");
    }

    private static IReadOnlyList<(bool Passed, string Name)> Run()
    {
        var checks = new List<(bool, string)>();
        void Check(bool condition, string name) => checks.Add((condition, name));
        var sequence = 0;
        string Id() => "id-" + Interlocked.Increment(ref sequence);
        var now = TimeSpan.FromSeconds(20);

        LightExecutionAuthorizationLedger Ledger(string process = "process-1") => new(process, Id);
        LightGateResult Gate(
            LightExecutionIntent intent = LightExecutionIntent.Desktop,
            LightGateDecisionKind decision = LightGateDecisionKind.Eligible,
            LightGateReasonCode reason = LightGateReasonCode.EligibleStableMatch,
            TimeSpan? evaluatedAt = null)
            => new(decision, reason, evaluatedAt ?? now, "watch-1", "profile-1",
                TimeSpan.FromMilliseconds(10), TimeSpan.FromSeconds(2), intent);

        LightAuthorizationRequest Request(
            LightArmLease arm,
            LightGateResult? gate = null,
            LightExecutionIntent intent = LightExecutionIntent.Desktop,
            string observation = "obs-1")
            => new(arm, gate ?? Gate(intent), intent, observation,
                "process-1", "watch-1", "profile-1", "pipeline-1",
                now, TimeSpan.FromMilliseconds(500), TimeSpan.FromMilliseconds(250),
                true, false, true, true);

        var ledger = Ledger();
        var arm = ledger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now - TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10));
        var issued = ledger.TryIssue(Request(arm));
        Check(issued.Succeeded && issued.ReasonCode == LightAuthorizationReasonCode.PermitIssued
              && issued.Permit?.Intent == LightExecutionIntent.Desktop,
            "eligible gate plus explicit arm issues identity-only permit");
        Check(ledger.TryIssue(Request(arm)).ReasonCode == LightAuthorizationReasonCode.ObservationAlreadyAuthorized,
            "one observation cannot issue two permits");

        var noArm = Ledger();
        var foreignArm = arm with { ArmGenerationId = "foreign" };
        Check(noArm.TryIssue(Request(foreignArm)).ReasonCode == LightAuthorizationReasonCode.NotArmed,
            "eligible gate without active arm is denied");
        Check(ledger.TryIssue(Request(arm, Gate(decision: LightGateDecisionKind.Denied,
                reason: LightGateReasonCode.CandidateOnly), observation: "obs-denied")).ReasonCode
              == LightAuthorizationReasonCode.GateDenied,
            "diagnostic denial cannot authorize execution");
        Check(ledger.TryIssue(Request(arm, Gate(reason: LightGateReasonCode.CandidateOnly),
                observation: "obs-inconsistent")).ReasonCode == LightAuthorizationReasonCode.GateReasonMismatch,
            "inconsistent eligible reason fails closed");
        Check(ledger.TryIssue(Request(arm, Gate(LightExecutionIntent.Game), observation: "obs-intent")).ReasonCode
              == LightAuthorizationReasonCode.GateReasonMismatch,
            "gate result is cryptographically scoped by exact evaluated intent data");

        var expiredLedger = Ledger();
        var expiredArm = expiredLedger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now - TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(1));
        Check(expiredLedger.TryIssue(Request(expiredArm)).ReasonCode == LightAuthorizationReasonCode.ArmExpired,
            "expired arm cannot issue permit");
        Check(ledger.TryIssue(Request(arm, Gate(evaluatedAt: now - TimeSpan.FromMilliseconds(501)),
                observation: "obs-stale")).ReasonCode == LightAuthorizationReasonCode.StaleGateResult,
            "gate result beyond freshness budget is denied");
        Check(ledger.TryIssue(Request(arm, observation: "obs-cancel") with { CancellationRequested = true }).ReasonCode
              == LightAuthorizationReasonCode.Cancelled,
            "cancellation revokes authorization before issue");

        var identityLedger = Ledger();
        var identityArm = identityLedger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now, TimeSpan.FromSeconds(10));
        Check(identityLedger.TryIssue(Request(identityArm, observation: "obs-process") with {
                ExpectedProcessGenerationId = "process-old" }).ReasonCode
              == LightAuthorizationReasonCode.ProcessGenerationChanged,
            "process restart generation mismatch is denied");
        Check(identityLedger.TryIssue(Request(identityArm, observation: "obs-watch") with {
                ExpectedWatchSessionId = "watch-old" }).ReasonCode
              == LightAuthorizationReasonCode.WatchSessionChanged,
            "Watch reconnect mismatch is denied");
        Check(identityLedger.TryIssue(Request(identityArm, observation: "obs-profile") with {
                ExpectedProfileRevision = "profile-old" }).ReasonCode
              == LightAuthorizationReasonCode.ProfileChanged,
            "profile revision mismatch is denied");
        Check(identityLedger.TryIssue(Request(identityArm, observation: "obs-pipeline") with {
                ExpectedPipelineRevision = "pipeline-old" }).ReasonCode
              == LightAuthorizationReasonCode.PipelineChanged,
            "pipeline revision mismatch is denied");
        Check(identityLedger.TryIssue(Request(identityArm, observation: "obs-policy") with {
                IntentAllowed = false }).ReasonCode == LightAuthorizationReasonCode.IntentNotAllowed,
            "caller allowlist defaults closed");

        var loginLedger = Ledger();
        var loginArm = loginLedger.Arm(LightExecutionIntent.Login, "watch-1", "profile-1", "pipeline-1",
            now, TimeSpan.FromSeconds(10));
        Check(loginLedger.TryIssue(Request(loginArm, Gate(LightExecutionIntent.Login),
                LightExecutionIntent.Login, "obs-login") with { IndependentEntryReasonKnown = false }).ReasonCode
              == LightAuthorizationReasonCode.IndependentReasonRequired,
            "shared Login/DC light state cannot select an entry reason");

        var consumeLedger = Ledger();
        var consumeArm = consumeLedger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now, TimeSpan.FromSeconds(10));
        var permit = consumeLedger.TryIssue(Request(consumeArm, observation: "obs-consume")).Permit!;
        var context = new LightPermitConsumeContext(permit.PermitId, LightExecutionIntent.Desktop,
            "process-1", "watch-1", "profile-1", "pipeline-1",
            now + TimeSpan.FromMilliseconds(100), true, false);
        var consumed = consumeLedger.TryConsume(context);
        Check(consumed.Succeeded && consumed.ReasonCode == LightAuthorizationReasonCode.PermitConsumed,
            "valid permit is atomically consumed");
        Check(consumeLedger.TryConsume(context).ReasonCode == LightAuthorizationReasonCode.AlreadyConsumed,
            "permit replay after consume is denied");

        var revokeLedger = Ledger();
        var revokeArm = revokeLedger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now, TimeSpan.FromSeconds(10));
        var revokedPermit = revokeLedger.TryIssue(Request(revokeArm, observation: "obs-revoke")).Permit!;
        Check(revokeLedger.RevokeAll(LightAuthorizationReasonCode.ProfileChanged) == 1
              && revokeLedger.TryConsume(context with { PermitId = revokedPermit.PermitId }).ReasonCode
                 == LightAuthorizationReasonCode.ProfileChanged,
            "profile Save revokes outstanding permit even when values could hash the same");

        var expireLedger = Ledger();
        var expireArm = expireLedger.Arm(LightExecutionIntent.Desktop, "watch-1", "profile-1", "pipeline-1",
            now, TimeSpan.FromSeconds(10));
        var expiring = expireLedger.TryIssue(Request(expireArm, observation: "obs-expire") with {
            PermitLifetime = TimeSpan.FromMilliseconds(10) }).Permit!;
        Check(expireLedger.TryConsume(context with {
                PermitId = expiring.PermitId, Now = now + TimeSpan.FromMilliseconds(10) }).ReasonCode
              == LightAuthorizationReasonCode.PermitExpired,
            "permit expiry boundary is exclusive and fail-closed");

        var permitProperties = typeof(LightExecutionPermit).GetProperties(BindingFlags.Public | BindingFlags.Instance);
        var ledgerFields = typeof(LightExecutionAuthorizationLedger)
            .GetFields(BindingFlags.Instance | BindingFlags.NonPublic);
        Check(permitProperties.All(x => !typeof(Delegate).IsAssignableFrom(x.PropertyType))
              && ledgerFields.All(x => !typeof(IBoardBridge).IsAssignableFrom(x.FieldType)),
            "permit and ledger contain no callback or bridge dependency");
        Check(typeof(LightExecutionAuthorizationLedger).GetEvents().Length == 0,
            "authorization ledger exposes no execution event");

        return checks;
    }
}

internal static class LightExecutionAuthorizationConcurrencyContract
{
    internal static async Task RunAsync()
    {
        var next = 0;
        string Id() => "concurrent-" + Interlocked.Increment(ref next);
        var now = TimeSpan.FromSeconds(30);
        var ledger = new LightExecutionAuthorizationLedger("process-c", Id);
        var arm = ledger.Arm(LightExecutionIntent.Desktop, "watch-c", "profile-c", "pipeline-c",
            now, TimeSpan.FromSeconds(5));
        var gate = new LightGateResult(LightGateDecisionKind.Eligible,
            LightGateReasonCode.EligibleStableMatch, now, "watch-c", "profile-c",
            TimeSpan.Zero, TimeSpan.FromSeconds(2), LightExecutionIntent.Desktop);
        var request = new LightAuthorizationRequest(arm, gate, LightExecutionIntent.Desktop, "obs-c",
            "process-c", "watch-c", "profile-c", "pipeline-c", now,
            TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(1), true, false, true, true);
        var permit = ledger.TryIssue(request).Permit
            ?? throw new InvalidOperationException("Concurrency setup could not issue a permit.");
        var context = new LightPermitConsumeContext(permit.PermitId, LightExecutionIntent.Desktop,
            "process-c", "watch-c", "profile-c", "pipeline-c",
            now + TimeSpan.FromMilliseconds(1), true, false);

        var results = await Task.WhenAll(Enumerable.Range(0, 16)
            .Select(_ => Task.Run(() => ledger.TryConsume(context))));
        if (results.Count(x => x.Succeeded) != 1
            || results.Count(x => x.ReasonCode == LightAuthorizationReasonCode.AlreadyConsumed) != 15)
            throw new InvalidOperationException("Concurrent permit consumption was not exactly-once.");
        Console.WriteLine("PASS: concurrent consumers produce exactly one successful consume");
    }
}
