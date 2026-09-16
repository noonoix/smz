using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Builds the board-owned combined Guard + portable-executor bundle. Classroom Studio only
/// authors and packages this output; the exported runtime is the post-copy source of truth.
/// </summary>
public static class PortableGuardBundle
{
    private static readonly IReadOnlyDictionary<PipelineKind, string> RouteFiles =
        new Dictionary<PipelineKind, string>
        {
            [PipelineKind.Desktop] = "desktop_steps.txt",
            [PipelineKind.LoginOrDc] = "login_or_dc_steps.txt",
            [PipelineKind.CharacterDashboard] = "character_dashboard_steps.txt",
            [PipelineKind.EnteringGameLoading] = "entering_game_loading_steps.txt",
            [PipelineKind.Game] = "game_steps.txt",
            [PipelineKind.Targeted] = "targeted_steps.txt",
            [PipelineKind.Resumable] = "resumable_steps.txt",
        };

    private static readonly string[] RuntimeFiles =
    {
        "plan_engine.py",
        "live_light_guard.py",
        "guard_transition.py",
        "error_policy.py",
    };

    public static IReadOnlyList<string> Export(
        string planPath,
        PipelineWorkspace workspace,
        IReadOnlyList<LightStateProfile> profiles,
        AppSettings settings,
        int screenW,
        int screenH,
        string sourceName,
        string machine)
    {
        ArgumentNullException.ThrowIfNull(workspace);
        ArgumentNullException.ThrowIfNull(profiles);
        ValidateProfiles(profiles);

        var fullPlanPath = Path.GetFullPath(planPath);
        var directory = Path.GetDirectoryName(fullPlanPath)
            ?? throw new IOException("مسیر bundle Portable نامعتبر است.");
        Directory.CreateDirectory(directory);

        var allSteps = workspace.Tabs.SelectMany(tab => tab.Steps).ToList();
        var written = new List<string>();

        // The existing exporter supplies the combined Pico code.py/boot.py baseline. The
        // transition manifest and portable route files below are the authoritative additions.
        written.AddRange(PicoFirmwareExporter.Export(
            fullPlanPath, allSteps, machine, "once", 1, 0, keyboardOnArm: false));

        foreach (var tab in workspace.Tabs)
        {
            var routePath = Path.Combine(directory, RouteFiles[tab.Kind]);
            var text = tab.Steps.Count == 0
                ? "PLAN|2\n"
                : PlanExporter.CompileOnce(tab.Steps.ToList(), settings, screenW, screenH,
                    sourceName + "#" + tab.Kind, machine).Text;
            AtomicWrite(routePath, Encoding.UTF8.GetBytes(text));
            written.Add(routePath);
        }

        var manifest = BuildManifest(workspace, profiles);
        var manifestPath = Path.Combine(directory, "guard-transition.json");
        AtomicWrite(manifestPath, Encoding.UTF8.GetBytes(manifest));
        written.Add(manifestPath);

        var calibrationPath = Path.Combine(directory, "guard-calibration.json");
        AtomicWrite(calibrationPath, Encoding.UTF8.GetBytes(BuildCalibration(profiles)));
        written.Add(calibrationPath);

        var runtimeDirectory = Path.Combine(AppContext.BaseDirectory, "portable-runtime");
        foreach (var runtime in RuntimeFiles)
        {
            var source = Path.Combine(runtimeDirectory, runtime);
            if (!File.Exists(source))
                throw new IOException("فایل runtime Guard پیدا نشد: " + runtime);
            var destination = Path.Combine(directory, runtime);
            AtomicWrite(destination, File.ReadAllBytes(source));
            written.Add(destination);
        }

        var hashesPath = Path.Combine(directory, "SHA256SUMS.txt");
        var filesForHash = written
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(File.Exists)
            .OrderBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
            .ToArray();
        var hashes = string.Join(Environment.NewLine, filesForHash.Select(path =>
            Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()
                + "  " + Path.GetFileName(path))) + Environment.NewLine;
        AtomicWrite(hashesPath, Encoding.UTF8.GetBytes(hashes));
        written.Add(hashesPath);

        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static string BuildEntryPlan(IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var routes = profiles.Select(profile =>
        {
            var low = (int)Math.Floor(profile.LuxMin);
            var high = (int)Math.Ceiling(profile.LuxMax);
            return string.Join(":", profile.Id, low, high, RouteFiles[KindFor(profile.Id)]);
        });
        return "PLAN|2\nSTATELOOP|poll=250|stable=750|hysteresis=1|timeout=1500|fallback=STOP|routes="
            + string.Join(",", routes) + "\n";
    }

    public static string BuildManifest(PipelineWorkspace workspace, IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var payload = new
        {
            format = 1,
            runtime = "combined-pico-guard-executor",
            pipelineVersion = PipelineWorkspace.FormatVersion,
            pipelineRevision = PipelineWorkspaceRevision.Compute(workspace),
            calibrationRevision = LightGuardAppAdapter.ComputeRevision(profiles),
            orderedStages = new[] { "desktop", "login-or-dc", "character-dashboard", "entering-game-loading", "game" },
            dcFallback = new { fromStages = new[] { 3, 4, 5 }, toStage = 2, context = "dc" },
            targeted = new { sideState = true, route = "targeted_steps.txt", returnTo = "game" },
            routes = RouteFiles.ToDictionary(pair => pair.Key.ToString(), pair => pair.Value),
            profiles = profiles.Select(profile => new
            {
                id = profile.Id,
                center = profile.LuxCenter,
                tolerance = profile.LuxTolerance,
                stableMs = profile.StableDurationMs,
            }),
        };
        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine;
    }

    public static string BuildCalibration(IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var payload = new
        {
            format = 1,
            revision = LightGuardAppAdapter.ComputeRevision(profiles),
            profiles = profiles.ToDictionary(profile => profile.Id, profile => new
            {
                center = profile.LuxCenter,
                tolerance = profile.LuxTolerance,
                stable_ms = profile.StableDurationMs,
            }),
        };
        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine;
    }

    private static void ValidateProfiles(IReadOnlyList<LightStateProfile> profiles)
    {
        if (profiles.Count != LightGuardCalibrationProtocol.ProfileIds.Count
            || LightGuardCalibrationProtocol.ProfileIds.Any(id => profiles.Count(profile => profile.Id == id) != 1)
            || profiles.Any(profile => !profile.IsValid))
            throw new InvalidDataException("Combined Portable bundle requires exactly six valid Guard profiles.");
    }

    private static PipelineKind KindFor(string profileId) => profileId switch
    {
        "desktop" => PipelineKind.Desktop,
        "login-or-dc" => PipelineKind.LoginOrDc,
        "character-dashboard" => PipelineKind.CharacterDashboard,
        "entering-game-loading" => PipelineKind.EnteringGameLoading,
        "game" => PipelineKind.Game,
        "targeted" => PipelineKind.Targeted,
        _ => throw new InvalidDataException("Unknown Guard profile: " + profileId),
    };

    private static void AtomicWrite(string path, byte[] bytes)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllBytes(temporary, bytes);
            File.Move(temporary, path, true);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }
}
