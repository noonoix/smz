using System.Collections.ObjectModel;
using Ams.UI.Services;

namespace Ams.UI.Models;

/// <summary>Six optical positions, one post-reboot route, and Resumable.</summary>
public enum PipelineKind
{
    Desktop = 0,
    Restart = 1,
    LoginOrDc = 2,
    CharacterDashboard = 3,
    EnteringGameLoading = 4,
    Game = 5,
    Targeted = 6,
    Resumable = 7,

    // Compatibility aliases for existing commands/export code. These aliases are
    // intentionally not visible tabs; legacy content is preserved separately on migration.
    Launch = Desktop,
    LaunchRecovery = LoginOrDc,
    MainRecovery = Targeted,
    Main = Game,
    ResumeEssentials = Resumable,
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
/// Owns six optical-position step trees, one post-reboot tree, and one Resumable tree.
/// Legacy documents are retained during migration and are never silently reassigned.
/// </summary>
public sealed class PipelineWorkspace
{
    public const int FormatVersion = 3;

    public ObservableCollection<PipelineTabDocument> Tabs { get; } = new()
    {
        new() { Kind = PipelineKind.Desktop, Title = "Desktop", FileName = "desktop_steps.txt" },
        new() { Kind = PipelineKind.Restart, Title = "Restart", FileName = "restart_steps.txt" },
        new() { Kind = PipelineKind.LoginOrDc, Title = "Login / DC", FileName = "login_or_dc_steps.txt" },
        new() { Kind = PipelineKind.CharacterDashboard, Title = "Character Dashboard", FileName = "character_dashboard_steps.txt" },
        new() { Kind = PipelineKind.EnteringGameLoading, Title = "Entering Game / Loading", FileName = "entering_game_loading_steps.txt" },
        new() { Kind = PipelineKind.Game, Title = "Game", FileName = "game_steps.txt" },
        new() { Kind = PipelineKind.Targeted, Title = "Targeted", FileName = "targeted_steps.txt" },
        new() { Kind = PipelineKind.Resumable, Title = "Resumable", FileName = "resumable_steps.txt" },
    };

    public Dictionary<string, List<StepNode>> LegacyPipelines { get; } = new(StringComparer.Ordinal);
    public bool HasLegacyPipelines => LegacyPipelines.Count > 0;
    public PipelineTabDocument this[PipelineKind kind] => Tabs.Single(x => x.Kind == kind);

    public static PipelineWorkspace FromLegacy(IEnumerable<StepNode> roots, PipelineKind target = PipelineKind.Game)
    {
        var workspace = new PipelineWorkspace();
        foreach (var root in roots)
        {
            DocumentService.FixParents(root, null);
            workspace[target].Steps.Add(root);
        }
        return workspace;
    }
}
