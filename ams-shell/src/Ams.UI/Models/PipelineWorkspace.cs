using System.Collections.ObjectModel;
using Ams.UI.Services;

namespace Ams.UI.Models;

/// <summary>Fixed browser-style step workspaces. Launch is shared by initial start and Auto Resume.</summary>
public enum PipelineKind
{
    Launch,
    Main,
    LaunchRecovery,
    MainRecovery,
    ResumeEssentials,
}

public sealed class PipelineTabDocument
{
    public PipelineKind Kind { get; init; }
    public string Title { get; init; } = "";
    public string FileName { get; init; } = "";
    public ObservableCollection<StepNode> Steps { get; } = new();
    public bool IsDirty { get; set; }
    public string? ValidationError { get; set; }
}

/// <summary>
/// Owns the five fixed step trees. Tabs are non-closable and have stable ordering so export,
/// checkpoint and recovery contracts never depend on UI position or a marked For Loop.
/// </summary>
public sealed class PipelineWorkspace
{
    public const int FormatVersion = 1;
    public ObservableCollection<PipelineTabDocument> Tabs { get; } = new()
    {
        new() { Kind = PipelineKind.Launch, Title = "Launch", FileName = "launch_steps.txt" },
        new() { Kind = PipelineKind.Main, Title = "Main", FileName = "plan.txt" },
        new() { Kind = PipelineKind.LaunchRecovery, Title = "Launch DC Recovery", FileName = "launch_recovery.txt" },
        new() { Kind = PipelineKind.MainRecovery, Title = "Main DC Recovery", FileName = "main_recovery.txt" },
        new() { Kind = PipelineKind.ResumeEssentials, Title = "Resume Essentials", FileName = "resume_essentials.txt" },
    };

    public PipelineTabDocument this[PipelineKind kind] => Tabs.Single(x => x.Kind == kind);

    /// <summary>Legacy .amsj files migrate losslessly: their original tree becomes Main.</summary>
    public static PipelineWorkspace FromLegacy(IEnumerable<StepNode> roots)
    {
        var workspace = new PipelineWorkspace();
        foreach (var root in roots)
        {
            DocumentService.FixParents(root, null);
            workspace[PipelineKind.Main].Steps.Add(root);
        }
        return workspace;
    }
}
