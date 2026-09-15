using System.Reflection;
using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class NonExecutingLightAuthorizationDiagnosticsContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = Run();
        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Non-executing authorization diagnostics results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Authorization diagnostics contract failed: {failed}");
    }

    private static IReadOnlyList<(bool Passed, string Name)> Run()
    {
        var checks = new List<(bool, string)>();
        void Check(bool condition, string name) => checks.Add((condition, name));
        var ids = 0;
        string Id() => "diag-" + Interlocked.Increment(ref ids);
        var now = TimeSpan.FromSeconds(50);
        var context = new LightAuthorizationDiagnosticContext(
            "watch-1", "profile-1", "pipeline-1", now, true, true);
        var gate = new LightGateResult(LightGateDecisionKind.Eligible,
            LightGateReasonCode.EligibleStableMatch, now, "watch-1", "profile-1",
            TimeSpan.Zero, TimeSpan.FromSeconds(2), LightExecutionIntent.Desktop);

        var allowed = NonExecutingLightAuthorizationDiagnostics.AllowedIntents;
        Check(allowed.SequenceEqual(new[]
            {
                LightExecutionIntent.Desktop,
                LightExecutionIntent.CharacterDashboard,
                LightExecutionIntent.EnteringGameLoading,
                LightExecutionIntent.Game,
                LightExecutionIntent.Targeted,
            }) && !allowed.Contains(LightExecutionIntent.Login)
               && !allowed.Contains(LightExecutionIntent.Disconnect),
            "initial UI allowlist excludes ambiguous Login and Disconnect intents");

        var diagnostics = new NonExecutingLightAuthorizationDiagnostics(
            "process-1", TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(2),
            TimeSpan.FromMilliseconds(500), Id);
        Check(diagnostics.CurrentPermit is null
              && diagnostics.Snapshot.State == LightAuthorizationDiagnosticState.Disarmed,
            "observation alone cannot issue a permit");
        Check(diagnostics.Issue(context, gate, "obs-1").ReasonCode
              == LightAuthorizationReasonCode.NotArmed,
            "manual Issue without manual Arm is denied");
        Check(diagnostics.Arm(context).State == LightAuthorizationDiagnosticState.Armed,
            "explicit Arm creates a diagnostic arm lease");
        var issued = diagnostics.Issue(context, gate, "obs-1");
        Check(issued.State == LightAuthorizationDiagnosticState.PermitIssued
              && issued.ReasonCode == LightAuthorizationReasonCode.PermitIssued
              && diagnostics.CurrentPermit is not null,
            "manual Issue creates an identity-only permit for eligible matching gate");
        var consumed = diagnostics.Consume(context with { Now = now + TimeSpan.FromMilliseconds(1) });
        Check(consumed.State == LightAuthorizationDiagnosticState.PermitConsumed
              && consumed.ReasonCode == LightAuthorizationReasonCode.PermitConsumed,
            "manual Consume changes ledger state only");
        Check(diagnostics.Consume(context with { Now = now + TimeSpan.FromMilliseconds(2) }).ReasonCode
              == LightAuthorizationReasonCode.AlreadyConsumed,
            "second diagnostic consume is denied");

        var denied = new NonExecutingLightAuthorizationDiagnostics("process-2", idFactory: Id);
        Check(denied.Arm(context with { WatchRunning = false }).ReasonCode
              == LightAuthorizationReasonCode.Disconnected,
            "Watch off prevents Arm");
        Check(denied.Arm(context with { ConnectionHealthy = false }).ReasonCode
              == LightAuthorizationReasonCode.Disconnected,
            "disconnect prevents Arm");
        denied.Arm(context);
        Check(denied.Issue(context, gate with {
                Decision = LightGateDecisionKind.Denied,
                ReasonCode = LightGateReasonCode.CandidateOnly }, "obs-denied").ReasonCode
              == LightAuthorizationReasonCode.GateDenied,
            "Candidate or denied gate cannot issue permit");
        Check(denied.SelectIntent(LightExecutionIntent.Login).ReasonCode
              == LightAuthorizationReasonCode.IntentNotAllowed,
            "Login cannot be selected without an independent reason source");

        var mismatch = new NonExecutingLightAuthorizationDiagnostics("process-3", idFactory: Id);
        mismatch.Arm(context);
        Check(mismatch.Issue(context with { PipelineRevision = "pipeline-2" }, gate, "obs-pipeline").ReasonCode
              == LightAuthorizationReasonCode.PipelineChanged,
            "pipeline change fails closed at Issue");
        Check(mismatch.Revoke(LightAuthorizationReasonCode.ProfileChanged).State
              == LightAuthorizationDiagnosticState.Revoked
              && mismatch.CurrentPermit is null,
            "profile lifecycle event revokes arm and permit");

        var expiry = new NonExecutingLightAuthorizationDiagnostics(
            "process-4", TimeSpan.FromSeconds(10), TimeSpan.FromMilliseconds(10),
            TimeSpan.FromMilliseconds(500), Id);
        expiry.Arm(context);
        expiry.Issue(context, gate, "obs-expire");
        Check(expiry.Consume(context with { Now = now + TimeSpan.FromMilliseconds(10) }).ReasonCode
              == LightAuthorizationReasonCode.PermitExpired,
            "diagnostic permit expiry boundary is fail-closed");

        var workspaceA = Workspace(reverseProps: false);
        var workspaceB = Workspace(reverseProps: true);
        var revision = PipelineWorkspaceRevision.Compute(workspaceA);
        Check(revision == PipelineWorkspaceRevision.Compute(workspaceB),
            "pipeline revision ignores property dictionary insertion order");
        workspaceB[PipelineKind.ResumeEssentials].Steps.Add(new StepNode { Type = "delay", Delay = 1 });
        Check(revision != PipelineWorkspaceRevision.Compute(workspaceB),
            "pipeline revision covers all five tabs");
        workspaceA[PipelineKind.Main].Steps[0].Children.Add(new StepNode { Type = "comment", Name = "child" });
        Check(revision != PipelineWorkspaceRevision.Compute(workspaceA),
            "pipeline revision covers nested step mutations");

        var fields = typeof(NonExecutingLightAuthorizationDiagnostics)
            .GetFields(BindingFlags.Instance | BindingFlags.NonPublic);
        Check(fields.All(x => !typeof(IBoardBridge).IsAssignableFrom(x.FieldType)
                              && !typeof(Delegate).IsAssignableFrom(x.FieldType)),
            "diagnostics controller stores no Bridge or executable delegate");
        Check(typeof(NonExecutingLightAuthorizationDiagnostics).GetEvents().Length == 0,
            "diagnostics controller exposes no execution event");

        return checks;
    }

    private static PipelineWorkspace Workspace(bool reverseProps)
    {
        var workspace = new PipelineWorkspace();
        var props = reverseProps
            ? new Dictionary<string, object?> { ["b"] = 2, ["a"] = 1 }
            : new Dictionary<string, object?> { ["a"] = 1, ["b"] = 2 };
        workspace[PipelineKind.Main].Steps.Add(new StepNode
        {
            Type = "delay", Name = "root", Delay = 10, DelayMax = 20, Props = props,
        });
        return workspace;
    }
}
