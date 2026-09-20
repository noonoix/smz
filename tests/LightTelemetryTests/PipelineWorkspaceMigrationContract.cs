using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class PipelineWorkspaceMigrationContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = new List<(bool Passed, string Name)>();
        void Check(bool value, string name) => checks.Add((value, name));

        var workspace = new PipelineWorkspace();
        Check(workspace.Tabs.Count == 8,
            "workspace exposes Restart, six optical tabs, and Resumable");
        Check(workspace.Tabs.Select(x => x.Kind).SequenceEqual(new[]
            {
                PipelineKind.Desktop,
                PipelineKind.Restart,
                PipelineKind.LoginOrDc,
                PipelineKind.CharacterDashboard,
                PipelineKind.EnteringGameLoading,
                PipelineKind.Game,
                PipelineKind.Targeted,
                PipelineKind.Resumable,
            }),
            "Restart is immediately after Desktop and Targeted remains present");

        const string legacy = "{\"app\":\"AMS\",\"pipelineVersion\":1,\"pipelines\":{"
            + "\"Launch\":[],\"Main\":[],\"LaunchRecovery\":[],\"MainRecovery\":[],\"ResumeEssentials\":[]}}";
        var migrated = PipelineWorkspaceSerializer.Deserialize(legacy);
        Check(migrated.Tabs.Count == 8 && migrated.LegacyPipelines.Count == 5
              && migrated[PipelineKind.Restart].Steps.Count == 0,
            "legacy trees are retained and the new Restart route starts empty");
        var saved = PipelineWorkspaceSerializer.Serialize(migrated);
        Check(saved.Contains("legacyPipelines", StringComparison.Ordinal)
              && saved.Contains("LaunchRecovery", StringComparison.Ordinal)
              && saved.Contains("\"Restart\"", StringComparison.Ordinal),
            "migration backup and Restart survive saving the version-3 workspace");

        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Pipeline workspace migration results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Pipeline workspace migration contract failed: {failed}");
    }
}
