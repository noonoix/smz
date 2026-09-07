using System.ComponentModel;
using Brush = System.Windows.Media.Brush;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Ams.UI.Models;

/// <summary>
/// One visible row in the AMK-style flat steps list. It carries the pastel scope tint;
/// v0.9.36 draws the selected scope as ONE overlay bracket at ListBox level (not one
/// border per row), so rows no longer own permanent guide bands or red-line fragments.
/// </summary>
public sealed partial class FlatStepRow : ObservableObject
{
    public StepNode Node { get; }
    public string Number { get; }        // "1.13.2" — hierarchical (design doc §4)
    public int Depth { get; }            // indent level
    public StepNode? ScopeKey { get; }   // innermost enclosing scope node (row-reuse guard)

    /// <summary>Full-row pastel tint (semi-transparent, so hover/selection blend through).</summary>
    public Brush RowBg { get; }

    /// <summary>v0.8.0 — accordion: rows with children show a ▾/▸ toggle; collapsed hides the subtree.</summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ToggleGlyph))]
    [NotifyPropertyChangedFor(nameof(ShowToggle))]
    private bool _isCollapsed;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(ToggleGlyph))]
    private bool _hasChildren;

    public string ToggleGlyph => IsCollapsed ? "▸" : "▾";
    // v0.9.34 — the accordion belongs on the If row (its children = the Then branch): always visible
    // once insertIfElse is on; Else rows show a toggle only when they actually have children.
    public bool ShowToggle => HasChildren
        || (Node.Type is "findImage" or "waitForSound" or "waitForLight" && PropEx.GetBool(Node.Props, "insertIfElse"));

    /// <summary>Called by the VM on every rebuild/reuse so the toggle reflects current state.</summary>
    public void RefreshStructure(bool collapsed)
    {
        IsCollapsed = collapsed;
        HasChildren = Node.Children.Count > 0;
    }

    public FlatStepRow(StepNode node, string number, int depth, Brush rowBg, StepNode? scopeKey)
    {
        Node = node;
        Number = number;
        Depth = depth;
        RowBg = rowBg;
        ScopeKey = scopeKey;
        node.PropertyChanged += OnNodeChanged;
    }

    private void OnNodeChanged(object? sender, PropertyChangedEventArgs e)
    {
        switch (e.PropertyName)
        {
            case nameof(StepNode.Name): OnPropertyChanged(nameof(Name)); break;
            case nameof(StepNode.Delay): OnPropertyChanged(nameof(Delay)); OnPropertyChanged(nameof(DelayText)); break;
            case nameof(StepNode.DelayMax): OnPropertyChanged(nameof(DelayText)); break;
            case nameof(StepNode.IsDisabled): OnPropertyChanged(nameof(IsDisabled)); break;
            case nameof(StepNode.Summary): OnPropertyChanged(nameof(Summary)); break;
        }
    }

    public string Type => Node.Type;
    public string Name => Node.Name;
    public string Summary => Node.Summary;
    public int Delay => Node.Delay;

    /// <summary>v0.7.8 — "1000–2000" when a random delay range is set, else the fixed value.</summary>
    public string DelayText => Node.DelayMax > Node.Delay ? $"{Node.Delay}–{Node.DelayMax}" : Node.Delay.ToString();
    public bool IsDisabled => Node.IsDisabled;

    /// <summary>Content indent — 22px per depth level.</summary>
    public Thickness Indent => new(Depth * 22, 0, 0, 0);

    /// <summary>v0.9.55 - marker rows (next / else / end if) own no accordion toggle, so their
    /// label reclaims that 14px gutter and sits tight against the red scope vein (user request).</summary>
    public bool IsMarkerRow => Node.Type == "comment"
        && StepDefinitions.IsStructuralMarker(PropEx.GetString(Node.Props, "text"));

    public Thickness SummaryInset => IsMarkerRow ? new Thickness(-12, 0, 0, 0) : new Thickness(0);

    // v0.9.47 — the structural Next label is deliberately NOT inset. Next is the loop's own
    // sibling, so it shares the loop's Depth/Indent, and the fixed 14px toggle column in the row
    // template makes both summary texts start at the exact same x ⇒ Next aligns with its head.
}
