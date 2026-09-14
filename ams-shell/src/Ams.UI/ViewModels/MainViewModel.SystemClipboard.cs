using System.Text.Json;
using Ams.UI.Models;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;
using WpfClipboard = System.Windows.Clipboard;

namespace Ams.UI.ViewModels;

/// <summary>
/// One versioned Windows clipboard payload is now used by shortcuts, menu items, context menus,
/// and the Cut/Copy/Paste commands. This removes the old split between the private in-process
/// clipboard and the Windows clipboard.
/// </summary>
public partial class MainViewModel
{
    private const string SystemStepClipboardPrefix = "AMS-STEPS-1\n";

    [RelayCommand]
    private void CopySystemClipboard()
    {
        var requested = EffectiveSelection();
        if (requested.Count == 0 || EditingText()) return;

        var (selected, ownedMarkers) = ExpandConditionalSelection(requested);
        var copyable = selected.Where(n => !IsStructuralMarker(n) || ownedMarkers.Contains(n)).ToList();
        if (copyable.Count < selected.Count)
            Log($"system copy blocked: {selected.Count - copyable.Count} structural marker(s) cannot be copied by themselves");
        if (copyable.Count == 0) return;

        var json = JsonSerializer.Serialize(copyable);
        _stepClipboardJson = json; // keep the legacy command as a safe in-process fallback
        try
        {
            WpfClipboard.SetText(SystemStepClipboardPrefix + json);
            Log($"copied {copyable.Count} step(s) to the Windows clipboard");
        }
        catch (Exception ex)
        {
            Log("system clipboard copy failed: " + ex.Message);
        }
    }

    [RelayCommand]
    private void CutSystemClipboard()
    {
        var requested = EffectiveSelection();
        if (requested.Count == 0 || EditingText()) return;

        var (selected, ownedMarkers) = ExpandConditionalSelection(requested);
        var cuttable = selected.Where(n => !IsStructuralMarker(n) || ownedMarkers.Contains(n)).ToList();
        if (cuttable.Count < selected.Count)
            Log($"system cut blocked: {selected.Count - cuttable.Count} structural marker(s) cannot be cut by themselves");
        if (cuttable.Count == 0) return;

        var json = JsonSerializer.Serialize(cuttable);
        try
        {
            WpfClipboard.SetText(SystemStepClipboardPrefix + json);
        }
        catch (Exception ex)
        {
            Log("system clipboard cut failed: " + ex.Message);
            return;
        }

        Snapshot();
        _stepClipboardJson = json;
        foreach (var node in cuttable)
            (node.Parent?.Children ?? Steps).Remove(node);
        SelectedNodes = new();
        SelectedNode = null;
        Renumber();
        MarkDirty();
        Log($"cut {cuttable.Count} step(s) to the Windows clipboard");
    }

    [RelayCommand]
    private void PasteSystemClipboard()
    {
        if (EditingText()) return;

        string text;
        try
        {
            if (!WpfClipboard.ContainsText()) return;
            text = WpfClipboard.GetText();
        }
        catch (Exception ex)
        {
            Log("system clipboard read failed: " + ex.Message);
            return;
        }

        var json = text.StartsWith(SystemStepClipboardPrefix, StringComparison.Ordinal)
            ? text[SystemStepClipboardPrefix.Length..].TrimStart()
            : text.TrimStart();
        if (!json.StartsWith("[") && !json.StartsWith("{"))
        {
            Log("paste skipped: the Windows clipboard does not contain AMS steps");
            return;
        }

        List<StepNode>? nodes;
        try
        {
            nodes = json.StartsWith("[")
                ? JsonSerializer.Deserialize<List<StepNode>>(json)
                : new List<StepNode> { JsonSerializer.Deserialize<StepNode>(json)! };
        }
        catch (Exception ex)
        {
            Log("paste skipped: invalid AMS step clipboard data — " + ex.Message);
            return;
        }
        if (nodes is null || nodes.Count == 0) return;

        Snapshot();
        var selected = SelectedNode;
        IList<StepNode> targetList;
        StepNode? parent;
        int insertAt;
        if (selected is not null && (StepDefinitions.AcceptsChildren(selected) || IsElseMarker(selected)))
        {
            targetList = selected.Children;
            parent = selected;
            insertAt = targetList.Count;
        }
        else if (selected is not null)
        {
            targetList = selected.Parent?.Children ?? Steps;
            parent = selected.Parent;
            insertAt = targetList.IndexOf(selected) + 1;
        }
        else
        {
            targetList = Steps;
            parent = null;
            insertAt = targetList.Count;
        }

        foreach (var node in nodes)
        {
            DocumentService.FixParents(node, parent);
            targetList.Insert(insertAt++, node);
        }
        foreach (var head in nodes.Where(IsIfElseHead)) EnsureElseMarkers(head);
        foreach (var loop in nodes.Where(OwnsNextMarker)) EnsureLoopMarker(loop);

        Renumber();
        SelectedNode = nodes.FirstOrDefault(IsIfElseHead) ?? nodes[^1];
        MarkDirty();
        Log($"pasted {nodes.Count} step(s) from the Windows clipboard");
    }
}
