using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Versioned persistence envelope for six optical-position tabs plus Resumable.</summary>
public static class PipelineWorkspaceSerializer
{
    private sealed class Envelope
    {
        public string app { get; set; } = "AMS";
        public int pipelineVersion { get; set; } = PipelineWorkspace.FormatVersion;
        public Dictionary<string, List<StepNode>> pipelines { get; set; } = new();
        public Dictionary<string, List<StepNode>> legacyPipelines { get; set; } = new();
    }

    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };

    // v1 .amsj files used five semantic buckets. Keep this mapping explicit instead
    // of silently opening the file as seven empty tabs.
    private static readonly IReadOnlyDictionary<string, string> LegacyToCurrent =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["Launch"] = "Desktop",
            ["LaunchRecovery"] = "LoginOrDc",
            ["Main"] = "Game",
            ["MainRecovery"] = "Targeted",
            ["ResumeEssentials"] = "Resumable",
        };

    public static string Serialize(PipelineWorkspace workspace)
    {
        var envelope = new Envelope();
        foreach (var tab in workspace.Tabs)
            envelope.pipelines[tab.Kind.ToString()] = tab.Steps.ToList();
        foreach (var pair in workspace.LegacyPipelines)
            envelope.legacyPipelines[pair.Key] = pair.Value;
        return JsonSerializer.Serialize(envelope, Options);
    }

    public static PipelineWorkspace Deserialize(string json)
    {
        var envelope = JsonSerializer.Deserialize<Envelope>(json, Options)
            ?? throw new InvalidDataException("Not an AMS pipeline document.");
        if (envelope.app != "AMS")
            throw new InvalidDataException("Unsupported AMS pipeline document.");
        if (envelope.pipelineVersion is not (1 or PipelineWorkspace.FormatVersion))
            throw new InvalidDataException("Unsupported AMS pipeline document.");

        var workspace = new PipelineWorkspace();
        if (envelope.pipelineVersion == PipelineWorkspace.FormatVersion)
        {
            foreach (var pair in envelope.legacyPipelines)
                workspace.LegacyPipelines[pair.Key] = pair.Value;
        }

        var currentNames = workspace.Tabs.Select(tab => tab.Kind.ToString()).ToHashSet(StringComparer.Ordinal);
        foreach (var pair in envelope.pipelines)
        {
            if (currentNames.Contains(pair.Key)) continue;
            if (envelope.pipelineVersion == 1 && LegacyToCurrent.TryGetValue(pair.Key, out var migrated))
                continue;
            workspace.LegacyPipelines[pair.Key] = pair.Value;
        }

        foreach (var tab in workspace.Tabs)
        {
            tab.Steps.Clear();
            List<StepNode>? roots = null;
            if (envelope.pipelines.TryGetValue(tab.Kind.ToString(), out var currentRoots))
                roots = currentRoots;
            else if (envelope.pipelineVersion == 1)
            {
                var legacyKey = LegacyToCurrent.FirstOrDefault(x => x.Value == tab.Kind.ToString()).Key;
                if (!string.IsNullOrEmpty(legacyKey)) envelope.pipelines.TryGetValue(legacyKey, out roots);
            }
            if (roots is null) continue;
            foreach (var root in roots)
            {
                DocumentService.FixParents(root, null);
                tab.Steps.Add(root);
            }
        }
        return workspace;
    }
}
