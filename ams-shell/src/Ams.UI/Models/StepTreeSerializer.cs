namespace Ams.UI.Models;

using System.Collections.Generic;
using System.Text.Json;

/// <summary>v0.9.30 — full-tree JSON snapshots for undo/redo. Same plain System.Text.Json
/// shape as DocumentService (.amsj files), so a snapshot round-trip is exactly as safe as
/// File→Save→Open. Restore rewires the [JsonIgnore] Parent links. Extracted for TestRunner
/// (step 30).</summary>
public static class StepTreeSerializer
{
    private static readonly JsonSerializerOptions Opts = new() { WriteIndented = true };

    public static string Snapshot(IEnumerable<StepNode> roots) => JsonSerializer.Serialize(roots, Opts);

    public static List<StepNode> Restore(string json)
    {
        var roots = JsonSerializer.Deserialize<List<StepNode>>(json, Opts) ?? new List<StepNode>();
        foreach (var n in roots) Rewire(n, null);
        return roots;
    }

    private static void Rewire(StepNode node, StepNode? parent)
    {
        node.Parent = parent;
        foreach (var c in node.Children) Rewire(c, node);
    }
}
