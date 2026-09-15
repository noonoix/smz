using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class NonExecutingLightAuthorizationLifecycleContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = new List<(bool Passed, string Name)>();
        void Check(bool condition, string name) => checks.Add((condition, name));

        var now = TimeSpan.FromSeconds(50);
        var context = new LightAuthorizationDiagnosticContext(
            "watch-1", "profile-1", "pipeline-1", now, true, true);
        var gate = new LightGateResult(
            LightGateDecisionKind.Eligible,
            LightGateReasonCode.EligibleStableMatch,
            now,
            "watch-1",
            "profile-1",
            TimeSpan.Zero,
            TimeSpan.FromSeconds(2),
            LightExecutionIntent.Desktop);
        var ids = 0;
        string Id() => "lifecycle-" + Interlocked.Increment(ref ids);
        var diagnostics = new NonExecutingLightAuthorizationDiagnostics(
            "process-lifecycle", idFactory: Id);

        Check(diagnostics.Arm(context).State == LightAuthorizationDiagnosticState.Armed,
            "lifecycle test starts with explicit Arm");
        var pipelineMismatch = diagnostics.Issue(
            context with { PipelineRevision = "pipeline-2" }, gate, "observation-1");
        Check(pipelineMismatch.ReasonCode == LightAuthorizationReasonCode.PipelineChanged
              && !diagnostics.CanIssue
              && !diagnostics.CanConsume
              && diagnostics.CurrentPermit is null,
            "pipeline mismatch immediately invalidates the local diagnostic lease");

        Check(diagnostics.Arm(context).State == LightAuthorizationDiagnosticState.Armed,
            "a revoked pipeline lease requires a new explicit Arm");
        var issued = diagnostics.Issue(context, gate, "observation-1");
        Check(issued.State == LightAuthorizationDiagnosticState.PermitIssued
              && !diagnostics.CanIssue
              && diagnostics.CanConsume,
            "Issue transitions the UI state to Consume-only");
        var consumed = diagnostics.Consume(context with { Now = now + TimeSpan.FromMilliseconds(1) });
        Check(consumed.State == LightAuthorizationDiagnosticState.PermitConsumed
              && !diagnostics.CanIssue
              && !diagnostics.CanConsume,
            "Consume closes the explicit Arm-Issue-Consume cycle");
        Check(diagnostics.Consume(context with { Now = now + TimeSpan.FromMilliseconds(2) }).ReasonCode
              == LightAuthorizationReasonCode.AlreadyConsumed,
            "the consumed ledger entry remains auditable as AlreadyConsumed");
        Check(diagnostics.Issue(context, gate, "observation-2").ReasonCode
              == LightAuthorizationReasonCode.NotArmed,
            "a consumed cycle cannot issue again without a new Arm");

        var disconnected = diagnostics.Arm(context).State == LightAuthorizationDiagnosticState.Armed
            && diagnostics.Arm(context with { ConnectionHealthy = false }).ReasonCode
                == LightAuthorizationReasonCode.Disconnected;
        Check(disconnected && diagnostics.CurrentPermit is null,
            "disconnect revokes any newly armed diagnostic state");

        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Authorization lifecycle results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Authorization lifecycle contract failed: {failed}");
    }
}
