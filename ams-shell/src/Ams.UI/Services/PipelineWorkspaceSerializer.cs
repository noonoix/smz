using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Versioned persistence envelope for optical, Restart, and Resumable tabs.</summary>
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
        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object
                || root.TryGetProperty("steps", out _)
                || !root.TryGetProperty("pipelines", out _))
                throw new InvalidDataException("Legacy AMS script document.");
        }
        catch (JsonException ex)
        {
            throw new InvalidDataException("Not an AMS pipeline document.", ex);
        }

        var envelope = JsonSerializer.Deserialize<Envelope>(json, Options)
            ?? throw new InvalidDataException("Not an AMS pipeline document.");
        if (envelope.app != "AMS")
            throw new InvalidDataException("Unsupported AMS pipeline document.");
        if (envelope.pipelineVersion is not (1 or 2 or PipelineWorkspace.FormatVersion))
            throw new InvalidDataException("Unsupported AMS pipeline document.");

        var workspace = new PipelineWorkspace();
        if (envelope.pipelineVersion >= 2)
        {
            foreach (var pair in envelope.legacyPipelines)
                workspace.LegacyPipelines[pair.Key] = pair.Value;
        }

        var currentNames = workspace.Tabs.Select(tab => tab.Kind.ToString()).ToHashSet(StringComparer.Ordinal);
        foreach (var pair in envelope.pipelines)
        {
            if (!currentNames.Contains(pair.Key))
                workspace.LegacyPipelines[pair.Key] = pair.Value;
        }

        foreach (var tab in workspace.Tabs)
        {
            tab.Steps.Clear();
            if (!envelope.pipelines.TryGetValue(tab.Kind.ToString(), out var roots)) continue;
            foreach (var root in roots)
            {
                DocumentService.FixParents(root, null);
                tab.Steps.Add(root);
            }
        }
        // Version 1/2 files did not have Restart; the new tab intentionally stays empty.
        return workspace;
    }
}
