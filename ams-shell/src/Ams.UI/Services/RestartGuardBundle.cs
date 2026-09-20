using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Adds the non-optical, post-reboot Restart route to the reviewed Guard bundle.</summary>
public static class RestartGuardBundle
{
    public const string RouteFile = "restart_steps.txt";

    public static IReadOnlyList<string> Export(string planPath, PipelineWorkspace workspace,
        IReadOnlyList<LightStateProfile> profiles, AppSettings settings, int screenW, int screenH,
        string sourceName, string machine)
    {
        var restart = workspace[PipelineKind.Restart];
        var opticalWorkspace = new PipelineWorkspace();
        opticalWorkspace.Tabs.Remove(opticalWorkspace[PipelineKind.Restart]);
        foreach (var target in opticalWorkspace.Tabs)
        {
            var source = workspace[target.Kind];
            foreach (var root in StepTreeSerializer.Restore(StepTreeSerializer.Snapshot(source.Steps)))
                target.Steps.Add(root);
        }
        foreach (var pair in workspace.LegacyPipelines)
            opticalWorkspace.LegacyPipelines[pair.Key] = pair.Value;

        var written = PortableGuardBundle.Export(planPath, opticalWorkspace, profiles, settings,
            screenW, screenH, sourceName, machine).ToList();
        var directory = Path.GetDirectoryName(Path.GetFullPath(planPath))
            ?? throw new IOException("مسیر bundle Restart نامعتبر است.");
        var restartPath = Path.Combine(directory, RouteFile);
        var restartText = restart.Steps.Count == 0 ? "PLAN|2\n" :
            CompileRoute(restart.Steps, settings, screenW, screenH, sourceName + "#Restart", machine);
        WriteAtomic(restartPath, Encoding.UTF8.GetBytes(restartText));
        written.Add(restartPath);

        var manifestPath = Path.Combine(directory, "guard-transition.json");
        var manifest = JsonNode.Parse(File.ReadAllText(manifestPath))?.AsObject()
            ?? throw new InvalidDataException("Guard manifest is not an object.");
        var routes = manifest["routes"]?.AsObject()
            ?? throw new InvalidDataException("Guard manifest routes are missing.");
        routes[nameof(PipelineKind.Restart)] = RouteFile;
        manifest["pipelineVersion"] = PipelineWorkspace.FormatVersion;
        manifest["pipelineRevision"] = PipelineWorkspaceRevision.Compute(workspace);
        WriteAtomic(manifestPath, new UTF8Encoding(false).GetBytes(
            manifest.ToJsonString(new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine));

        RebuildHashes(directory, written);
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    private static string CompileRoute(IEnumerable<StepNode> steps, AppSettings settings,
        int screenW, int screenH, string sourceName, string machine)
    {
        var normalized = NormalizePortableSteps(steps);
        const string sentinel = "__COMBINED_GUARD_PORTABLE_OP__";
        var text = PlanExporter.CompileOnce(normalized, settings, screenW, screenH, sourceName, machine).Text;
        return string.Join("\n", text.Split('\n').Select(line =>
            line.StartsWith("# " + sentinel, StringComparison.Ordinal)
                ? line[(2 + sentinel.Length)..]
                : line));
    }

    private static List<StepNode> NormalizePortableSteps(IEnumerable<StepNode> nodes)
    {
        const string sentinel = "__COMBINED_GUARD_PORTABLE_OP__";
        var result = new List<StepNode>();
        foreach (var source in nodes)
        {
            if (source.Type == "buzzer" && !source.IsDisabled)
            {
                foreach (var command in StepDefinitions.BuildBuzzerCommands(source.Props))
                {
                    var portable = command.StartsWith("DLY|", StringComparison.Ordinal)
                        ? "DELAY|" + command[4..] : command;
                    result.Add(new StepNode { Type = "comment", Name = source.Name,
                        Props = new Dictionary<string, object?> { ["text"] = sentinel + portable } });
                }
                if (source.Delay > 0 || source.DelayMax > 0)
                    result.Add(new StepNode { Type = "delay", Props = new Dictionary<string, object?>
                    {
                        ["minMs"] = source.Delay,
                        ["maxMs"] = source.DelayMax > 0 ? source.DelayMax : source.Delay,
                    }});
                continue;
            }
            var clone = new StepNode { Type = source.Type, Name = source.Name, Delay = source.Delay,
                DelayMax = source.DelayMax, IsDisabled = source.IsDisabled,
                Props = new Dictionary<string, object?>(source.Props) };
            foreach (var child in NormalizePortableSteps(source.Children))
            {
                child.Parent = clone;
                clone.Children.Add(child);
            }
            result.Add(clone);
        }
        return result;
    }

    public static void RebuildHashes(string directory, IEnumerable<string> written)
    {
        var hashPath = Path.Combine(directory, "SHA256SUMS.txt");
        var files = written.Where(File.Exists)
            .Where(path => !string.Equals(Path.GetFileName(path), "SHA256SUMS.txt", StringComparison.OrdinalIgnoreCase))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase).ToArray();
        var hashes = string.Join(Environment.NewLine, files.Select(path =>
            Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()
            + "  " + Path.GetFileName(path))) + Environment.NewLine;
        WriteAtomic(hashPath, new UTF8Encoding(false).GetBytes(hashes));
    }

    private static void WriteAtomic(string path, byte[] bytes)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try { File.WriteAllBytes(temporary, bytes); File.Move(temporary, path, true); }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
}
