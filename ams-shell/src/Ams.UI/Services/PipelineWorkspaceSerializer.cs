using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Versioned persistence envelope for browser-style pipeline tabs.</summary>
public static class PipelineWorkspaceSerializer
{
    private sealed class Envelope
    {
        public string? app { get; set; }
        public int? pipelineVersion { get; set; }
        public Dictionary<string, List<StepNode>>? pipelines { get; set; }
    }

    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };

    public static string Serialize(PipelineWorkspace workspace)
    {
        var envelope = new Envelope
        {
            app = "AMS",
            pipelineVersion = PipelineWorkspace.FormatVersion,
            pipelines = new(),
        };
        foreach (var tab in workspace.Tabs)
            envelope.pipelines![tab.Kind.ToString()] = tab.Steps.ToList();
        return JsonSerializer.Serialize(envelope, Options);
    }

    public static PipelineWorkspace Deserialize(string json)
    {
        var envelope = JsonSerializer.Deserialize<Envelope>(json, Options)
            ?? throw new InvalidDataException("Not an AMS pipeline document.");

        // Legacy .amsj documents use { app, version, steps }. These members must stay
        // nullable here: defaulting them made a legacy document look like a valid empty
        // pipeline and prevented OpenPipelineWorkspace from running its migration path.
        if (envelope.app != "AMS" || envelope.pipelineVersion is null || envelope.pipelines is null)
            throw new InvalidDataException("Not an AMS pipeline document.");
        if (envelope.pipelineVersion.Value != PipelineWorkspace.FormatVersion)
            throw new InvalidDataException("Unsupported AMS pipeline document.");

        var workspace = new PipelineWorkspace();
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
        return workspace;
    }
}
