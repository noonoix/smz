using System.Collections.ObjectModel;
using System.Text.Json.Serialization;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Ams.UI.Models;

/// <summary>
/// One step of the script tree. Mirrors the AMK record model (design doc §9.2):
/// NAME (step name) · DLY (delay after step) · DIS (disabled) · SUB (children).
/// </summary>
public partial class StepNode : ObservableObject
{
    /// <summary>Step type key from <see cref="StepDefinitions"/> (mouseClick, keystroke, forLoop, …).</summary>
    public string Type { get; set; } = "";

    /// <summary>AMK NAME — free-text label shown in the tree.</summary>
    [ObservableProperty] private string _name = "";

    /// <summary>AMK DLY — delay after step in ms.</summary>
    [ObservableProperty] private int _delay;

    /// <summary>v0.7.8 — optional upper bound of the after-step delay. When greater than
    /// Delay, the runner waits a random time in [Delay, DelayMax] on every pass (AMK's
    /// RAND+WAIT pattern — per-step humanizing). 0 = fixed delay. Omitted from .amsj when 0.</summary>
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    [ObservableProperty] private int _delayMax;

    /// <summary>AMK DIS — disabled steps are greyed out and skipped by the runner (§9.5).</summary>
    [ObservableProperty] private bool _isDisabled;

    /// <summary>Hierarchical display number like "1.13.2" (§4). UI-only — recomputed on every structural change.</summary>
    [property: JsonIgnore]
    [ObservableProperty] private string _number = "";

    /// <summary>Type-specific parameters (validated by the step dialog).</summary>
    public Dictionary<string, object?> Props { get; set; } = new();

    /// <summary>Nested steps: loop bodies / If-Else branches (AMK SUB records).</summary>
    /// <summary>Nested steps: loop bodies / If-Else branches (AMK SUB records).
    /// v0.7.1: setter added — System.Text.Json then reliably deserializes the "Children"
    /// arrays on Open (the get-only populate path silently dropped them → flat tree).</summary>
    public ObservableCollection<StepNode> Children { get; set; } = new();

    [JsonIgnore] public StepNode? Parent { get; set; }

    [JsonIgnore] public string Summary => StepDefinitions.Summarize(this);

    public void RefreshSummary() => OnPropertyChanged(nameof(Summary));
}
