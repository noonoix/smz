using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Exports every first-class pipeline tab with the ordinary PLAN|2 compiler.</summary>
public static class PipelinePlanBundle
{
    private const string MainSentinel = "__PIPELINE_CALL_MAIN_DC_RECOVERY__";
    private const string LaunchSentinel = "__PIPELINE_CALL_LAUNCH_DC_RECOVERY__";

    public static IReadOnlyList<string> Export(string planPath, PipelineWorkspace workspace,
        AppSettings settings, int screenW, int screenH, string sourceName, string machine)
    {
        ValidateRecoveryCalls(workspace);
        var mainSteps = NormalizeRecoveryCalls(workspace[PipelineKind.Main].Steps);
        var written = AutoCyclePlanBundle.Export(planPath, mainSteps,
            settings, screenW, screenH, sourceName + "#main", machine).ToList();
        var directory = Path.GetDirectoryName(Path.GetFullPath(planPath))
            ?? throw new IOException("مسیر خروجی Pipeline نامعتبر است.");

        var rootText = ExpandRecoveryCalls(File.ReadAllText(Path.GetFullPath(planPath)));
        AtomicWrite(Path.GetFullPath(planPath), new UTF8Encoding(false).GetBytes(rootText));
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

        var recoverySource = Path.Combine(AppContext.BaseDirectory, "portable-runtime", "recovery_runtime.py");
        if (!File.Exists(recoverySource)) throw new IOException("فایل runtime بازیابی پیدا نشد: recovery_runtime.py");
        var recoveryTarget = Path.Combine(directory, "recovery_runtime.py");
        AtomicWrite(recoveryTarget, File.ReadAllBytes(recoverySource));
        written.Add(recoveryTarget);
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();

        (string Name, byte[] Bytes) Compile(PipelineKind kind, string name)
        {
            var normalized = NormalizeRecoveryCalls(workspace[kind].Steps);
            var text = normalized.Count == 0 ? "PLAN|2\n" : PlanExporter.CompileOnce(normalized, settings, screenW, screenH, sourceName + "#" + kind, machine).Text;
            text = ExpandRecoveryCalls(text);
            if (text.Contains("RUNFOR|", StringComparison.Ordinal) || text.Contains("AUTORESUME|", StringComparison.Ordinal) || text.Contains("POSTLAUNCH|", StringComparison.Ordinal))
                throw new PlanExporter.PlanBlockedException(new[] { name + ": directive چرخه فقط در plan.txt مجاز است." });
            return (name, new UTF8Encoding(false).GetBytes(text));
        }
    }

    private static void ValidateRecoveryCalls(PipelineWorkspace workspace)
    {
        var errors = new List<string>();
        foreach (var tab in workspace.Tabs) Visit(tab.Steps, tab.Kind, tab.Title, errors);
        if (errors.Count > 0) throw new PlanExporter.PlanBlockedException(errors);
        static void Visit(IEnumerable<StepNode> nodes, PipelineKind kind, string title, List<string> errors)
        {
            foreach (var node in nodes)
            {
                if (node.Type == RecoveryCallStepDefinitions.CallMain && kind != PipelineKind.Main) errors.Add(title + ": استپ Run/Call Main DC Recovery فقط در تب Main مجاز است.");
                if (node.Type == RecoveryCallStepDefinitions.CallLaunch && kind != PipelineKind.Launch) errors.Add(title + ": استپ Run/Call Launch DC Recovery فقط در تب Launch مجاز است.");
                Visit(node.Children, kind, title, errors);
            }
        }
    }

    private static List<StepNode> NormalizeRecoveryCalls(IEnumerable<StepNode> nodes)
    {
        var result = new List<StepNode>();
        foreach (var source in nodes)
        {
            var mapped = source.Type switch { RecoveryCallStepDefinitions.CallMain => MainSentinel, RecoveryCallStepDefinitions.CallLaunch => LaunchSentinel, _ => null };
            var clone = new StepNode
            {
                Type = mapped is null ? source.Type : "comment", Name = source.Name, Delay = source.Delay,
                DelayMax = source.DelayMax, IsDisabled = source.IsDisabled,
                Props = mapped is null ? new Dictionary<string, object?>(source.Props) : new Dictionary<string, object?> { ["text"] = mapped },
            };
            foreach (var child in NormalizeRecoveryCalls(source.Children)) { child.Parent = clone; clone.Children.Add(child); }
            result.Add(clone);
        }
        return result;
    }

    private static string ExpandRecoveryCalls(string text)
        => text.Replace("# " + MainSentinel, "INCLUDE|file=main_recovery.txt", StringComparison.Ordinal)
               .Replace("# " + LaunchSentinel, "INCLUDE|file=launch_recovery.txt", StringComparison.Ordinal);

    private static void AtomicWrite(string path, byte[] bytes)
    {
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try { File.WriteAllBytes(temp, bytes); File.Move(temp, path, true); }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
}
