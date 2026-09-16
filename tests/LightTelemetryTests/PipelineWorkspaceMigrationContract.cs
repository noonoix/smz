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
        Check(workspace.Tabs.Count == 7,
            "workspace exposes six optical tabs plus Resumable");
        Check(workspace.Tabs.Select(x => x.Kind).SequenceEqual(new[]
            {
                PipelineKind.Desktop,
                PipelineKind.LoginOrDc,
                PipelineKind.CharacterDashboard,
                PipelineKind.EnteringGameLoading,
                PipelineKind.Game,
                PipelineKind.Targeted,
                PipelineKind.Resumable,
            }),
            "visible tabs use canonical Guard profile order");

        const string legacy = "{\"app\":\"AMS\",\"pipelineVersion\":1,\"pipelines\":{"
            + "\"Launch\":[],\"Main\":[],\"LaunchRecovery\":[],\"MainRecovery\":[],\"ResumeEssentials\":[]}}";
        var migrated = PipelineWorkspaceSerializer.Deserialize(legacy);
        Check(migrated.Tabs.Count == 7 && migrated.LegacyPipelines.Count == 5,
            "legacy five-tab trees are retained as migration backup");
        var saved = PipelineWorkspaceSerializer.Serialize(migrated);
        Check(saved.Contains("legacyPipelines", StringComparison.Ordinal)
              && saved.Contains("LaunchRecovery", StringComparison.Ordinal),
            "migration backup survives saving the version-2 workspace");

        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Pipeline workspace migration results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Pipeline workspace migration contract failed: {failed}");
    }
}
