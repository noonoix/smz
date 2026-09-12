using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Exports every first-class pipeline tab with the ordinary PLAN|2 compiler.</summary>
public static class PipelinePlanBundle
{
    public static IReadOnlyList<string> Export(string planPath, PipelineWorkspace workspace,
        AppSettings settings, int screenW, int screenH, string sourceName, string machine)
    {
        var written = AutoCyclePlanBundle.Export(planPath, workspace[PipelineKind.Main].Steps,
            settings, screenW, screenH, sourceName + "#main", machine).ToList();
        var directory = Path.GetDirectoryName(Path.GetFullPath(planPath))
            ?? throw new IOException("مسیر خروجی Pipeline نامعتبر است.");

        var payloads = new[]
        {
            Compile(PipelineKind.Launch, "launch_steps.txt"),
            Compile(PipelineKind.LaunchRecovery, "launch_recovery.txt"),
            Compile(PipelineKind.MainRecovery, "main_recovery.txt"),
            Compile(PipelineKind.ResumeEssentials, "resume_essentials.txt"),
        };
        foreach (var payload in payloads)
        {
            var path = Path.Combine(directory, payload.Name);
            AtomicWrite(path, payload.Bytes);
            written.Add(path);
        }
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();

        (string Name, byte[] Bytes) Compile(PipelineKind kind, string name)
        {
            var tab = workspace[kind];
            var text = tab.Steps.Count == 0
                ? "PLAN|2\n"
                : PlanExporter.CompileOnce(tab.Steps, settings, screenW, screenH,
                    sourceName + "#" + kind, machine).Text;
            if (text.Contains("RUNFOR|", StringComparison.Ordinal)
                || text.Contains("AUTORESUME|", StringComparison.Ordinal)
                || text.Contains("POSTLAUNCH|", StringComparison.Ordinal))
                throw new PlanExporter.PlanBlockedException(new[] { name + ": directive چرخه فقط در plan.txt مجاز است." });
            return (name, new UTF8Encoding(false).GetBytes(text));
        }
    }

    private static void AtomicWrite(string path, byte[] bytes)
    {
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllBytes(temp, bytes);
            File.Move(temp, path, true);
        }
        finally
        {
            if (File.Exists(temp)) File.Delete(temp);
        }
    }
}
