using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Builds the board-owned combined Guard + portable-executor bundle.</summary>
public static class PortableGuardBundle
{
    public const string ExporterVersion = "0.9.67";

    private static readonly IReadOnlyDictionary<PipelineKind, string> RouteFiles = new Dictionary<PipelineKind, string>
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
        "plan_engine.py", "live_light_guard.py", "guard_transition.py", "guard_calibration_protocol.py", "error_policy.py", "combined_guard_runtime.py",
    };

    private static readonly string[] CombinedFirmwareFiles = { "code.py", "boot.py" };

    public static readonly IReadOnlyList<string> ExpectedBundleFiles = new[]
    {
        "boot.py", "character_dashboard_steps.txt", "code.py", "combined_guard_runtime.py",
        "desktop_steps.txt", "entering_game_loading_steps.txt", "error_policy.py", "game_steps.txt",
        "guard-calibration.json", "guard-transition.json", "guard_calibration_protocol.py",
        "guard_transition.py", "live_light_guard.py", "login_or_dc_steps.txt", "pico-calibration.json",
        "plan.txt", "plan_engine.py", "README-FLASH.md", "resumable_steps.txt", "SHA256SUMS.txt",
        "targeted_steps.txt",
    };

    public static IReadOnlyList<string> Export(string planPath, PipelineWorkspace workspace,
        IReadOnlyList<LightStateProfile> profiles, AppSettings settings, int screenW, int screenH,
        string sourceName, string machine)
    {
        ArgumentNullException.ThrowIfNull(workspace);
        ArgumentNullException.ThrowIfNull(profiles);
        ValidateProfiles(profiles);
        ValidateWorkspace(workspace);

        var fullPlanPath = Path.GetFullPath(planPath);
        var directory = Path.GetDirectoryName(fullPlanPath) ?? throw new IOException("مسیر bundle Portable نامعتبر است.");
        Directory.CreateDirectory(directory);
        var runtimeDirectory = Path.Combine(AppContext.BaseDirectory, "portable-runtime");
        var combinedDirectory = Path.Combine(AppContext.BaseDirectory, "combined-runtime");
        var runtimeSources = RuntimeFiles.Select(name => (Name: name, Path: Path.Combine(runtimeDirectory, name))).ToArray();
        var firmwareSources = CombinedFirmwareFiles.Select(name => (Name: name, Path: Path.Combine(combinedDirectory, name))).ToArray();
        var missing = runtimeSources.Concat(firmwareSources).Where(item => !File.Exists(item.Path)).Select(item => item.Name).ToArray();
        if (missing.Length > 0) throw new IOException("فایل runtime Combined Guard پیدا نشد: " + string.Join(", ", missing));

        var routeTexts = workspace.Tabs.ToDictionary(tab => tab.Kind, tab => tab.Steps.Count == 0 ? "PLAN|2\n" :
            PlanExporter.CompileOnce(tab.Steps.ToList(), settings, screenW, screenH, sourceName + "#" + tab.Kind, machine).Text);
        var written = new List<string>();
        var codePath = Path.Combine(directory, "code.py");
        written.AddRange(PicoFirmwareExporter.Export(codePath, workspace.Tabs.SelectMany(tab => tab.Steps).ToList(), machine, "once", 1, 0, false));

        // The legacy per-system exporter provides compatibility files, but its README and
        // metadata describe the old four-file/adafruit_hid package. Replace both before
        // hashing so a Combined Guard bundle can never ship stale installation guidance.
        var picoCalibrationPath = Path.Combine(directory, "pico-calibration.json");
        AtomicWrite(picoCalibrationPath, Encoding.UTF8.GetBytes(BuildPicoCalibrationMetadata(profiles, machine)));
        var readmePath = Path.Combine(directory, "README-FLASH.md");
        AtomicWrite(readmePath, Encoding.UTF8.GetBytes(BuildReadme(machine)));

        foreach (var firmware in firmwareSources)
        {
            var destination = Path.Combine(directory, firmware.Name);
            AtomicWrite(destination, File.ReadAllBytes(firmware.Path));
            written.Add(destination);
        }
        foreach (var tab in workspace.Tabs)
        {
            var routePath = Path.Combine(directory, RouteFiles[tab.Kind]);
            AtomicWrite(routePath, Encoding.UTF8.GetBytes(routeTexts[tab.Kind]));
            written.Add(routePath);
        }
        var entryPlanPath = Path.Combine(directory, "plan.txt");
        AtomicWrite(entryPlanPath, Encoding.UTF8.GetBytes(BuildEntryPlan(profiles)));
        written.Add(entryPlanPath);
        var manifestPath = Path.Combine(directory, "guard-transition.json");
        AtomicWrite(manifestPath, Encoding.UTF8.GetBytes(BuildManifest(workspace, profiles)));
        written.Add(manifestPath);
        var calibrationPath = Path.Combine(directory, "guard-calibration.json");
        AtomicWrite(calibrationPath, Encoding.UTF8.GetBytes(BuildCalibration(profiles)));
        written.Add(calibrationPath);
        foreach (var runtime in runtimeSources)
        {
            var destination = Path.Combine(directory, runtime.Name);
            AtomicWrite(destination, File.ReadAllBytes(runtime.Path));
            written.Add(destination);
        }
        var hashesPath = Path.Combine(directory, "SHA256SUMS.txt");
        var files = written.Distinct(StringComparer.OrdinalIgnoreCase).Where(File.Exists).OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase).ToArray();
        var hashes = string.Join(Environment.NewLine, files.Select(path => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() + "  " + Path.GetFileName(path))) + Environment.NewLine;
        AtomicWrite(hashesPath, Encoding.UTF8.GetBytes(hashes));
        written.Add(hashesPath);

        var actualNames = written.Select(Path.GetFileName).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToArray();
        var expectedNames = ExpectedBundleFiles.OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToArray();
        if (!actualNames.SequenceEqual(expectedNames, StringComparer.OrdinalIgnoreCase))
            throw new InvalidDataException("Combined Guard bundle inventory mismatch.");
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static string BuildEntryPlan(IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var routes = profiles.Select(profile => string.Join(":", profile.Id, (int)Math.Floor(profile.LuxMin), (int)Math.Ceiling(profile.LuxMax), RouteFiles[KindFor(profile.Id)]));
        return "PLAN|2\nSTATELOOP|poll=250|stable=750|hysteresis=1|timeout=1500|fallback=STOP|routes=" + string.Join(",", routes) + "\n";
    }

    public static string BuildManifest(PipelineWorkspace workspace, IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var payload = new
        {
            format = 1, runtime = "combined-pico-guard-executor", pipelineVersion = PipelineWorkspace.FormatVersion,
            pipelineRevision = PipelineWorkspaceRevision.Compute(workspace), calibrationRevision = LightGuardAppAdapter.ComputeRevision(profiles),
            orderedStages = new[] { "desktop", "login-or-dc", "character-dashboard", "entering-game-loading", "game" },
            dcFallback = new { fromStages = new[] { 3, 4, 5 }, toStage = 2, context = "dc" },
            targeted = new { sideState = true, route = "targeted_steps.txt", returnTo = "game" },
            routes = RouteFiles.ToDictionary(pair => pair.Key.ToString(), pair => pair.Value),
            profiles = profiles.Select(profile => new { id = profile.Id, center = profile.LuxCenter, tolerance = profile.LuxTolerance, stableMs = profile.StableDurationMs }),
        };
        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine;
    }

    public static string BuildCalibration(IReadOnlyList<LightStateProfile> profiles)
    {
        ValidateProfiles(profiles);
        var payload = new { format = 1, revision = LightGuardAppAdapter.ComputeRevision(profiles), profiles = profiles.ToDictionary(p => p.Id, p => new { center = p.LuxCenter, tolerance = p.LuxTolerance, stable_ms = p.StableDurationMs }) };
        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine;
    }

    public static string BuildPicoCalibrationMetadata(IReadOnlyList<LightStateProfile> profiles, string machine)
    {
        ValidateProfiles(profiles);
        var payload = new
        {
            generator = "Classroom Studio v" + ExporterVersion,
            bundle = "combined-pico-guard-executor",
            system = machine,
            generatedUtc = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss", System.Globalization.CultureInfo.InvariantCulture),
            hardwareCalibrationVerified = false,
            calibrationRevision = LightGuardAppAdapter.ComputeRevision(profiles),
            sensor = new { chip = "BH1750", board = "GY-302/GY-30", i2c = "I2C0 SDA=GP20 SCL=GP21", addr = 35 },
            states = Array.Empty<object>(),
        };
        return JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine;
    }

    public static string BuildReadme(string machine)
    {
        var files = string.Join("\n", ExpectedBundleFiles.Select(name => "- `" + name + "`"));
        return $"""
# Classroom Studio Combined Guard bundle — {machine}

Generated by Classroom Studio v{ExporterVersion}.

## Safety gate

This is a complete 21-file staging bundle for the Phase 7 combined Pico Guard executor. It is not hardware acceptance. Keep Guard OFF and do not press GP4/GP3 until provenance, `SHA256SUMS.txt`, and physical calibration have been reviewed. `pico-calibration.json` intentionally records `hardwareCalibrationVerified: false`; `guard-calibration.json` is the six-profile runtime calibration source of truth.

Validated target: Raspberry Pi Pico running CircuitPython 10.3.0. This runtime includes its own small HID keyboard driver. Do not install or copy `adafruit_hid`; it is not a dependency of `combined_guard_runtime.py`.

## Complete bundle inventory

{files}

All files must stay together at the root of the staging directory. `SHA256SUMS.txt` contains hashes for the other 20 files. Do not copy a partial subset to `CIRCUITPY`.

## Wiring contract

- BH1750/GY-302/GY-30: `VCC -> 3V3`, `GND -> GND`, `SDA -> GP20`, `SCL -> GP21`, `ADDR -> GND` (`0x23`).
- GP4: Start/Stop only after the installation and calibration gates are explicitly opened.
- GP3: Pass/Next only during the controlled calibration procedure.
- GP6: passive piezo.
- UART0 to Arduino arm: GP16 TX, GP17 RX, 57600 8N1, common GND.

## Controlled installation sequence

1. Keep the PR Draft and verify artifact provenance against the reviewed source commit.
2. Export into a new empty staging directory; verify all 20 manifest hashes and the exact 21-file inventory.
3. Confirm `combined_guard_runtime.py` has no `adafruit_hid` import and no `class Keycode`.
4. Only after an explicit installation approval, copy the complete bundle to a freshly prepared `CIRCUITPY` root.
5. Boot fail-closed with Guard OFF; do not start a route.
6. Perform the six-profile physical calibration, sync the revision, and verify `CALGET` before any Guard ON or route execution.

## Runtime files

`code.py` imports `combined_guard_runtime.main`. The runtime validates the bundle and hashes before operation. Empty route files contain only `PLAN|2` and perform no steps.
""" + Environment.NewLine;
    }

    private static void ValidateProfiles(IReadOnlyList<LightStateProfile> profiles)
    {
        if (profiles.Count != LightGuardCalibrationProtocol.ProfileIds.Count || LightGuardCalibrationProtocol.ProfileIds.Any(id => profiles.Count(p => p.Id == id) != 1) || profiles.Any(p => !p.IsValid))
            throw new InvalidDataException("Combined Portable bundle requires exactly six valid Guard profiles.");
    }
    private static void ValidateWorkspace(PipelineWorkspace workspace)
    {
        if (workspace.Tabs.Count != RouteFiles.Count || workspace.Tabs.Select(t => t.Kind).Distinct().Count() != RouteFiles.Count || RouteFiles.Keys.Any(k => !workspace.Tabs.Any(t => t.Kind == k)))
            throw new InvalidDataException("Combined Portable bundle requires the seven canonical route tabs.");
    }
    private static PipelineKind KindFor(string id) => id switch
    {
        "desktop" => PipelineKind.Desktop, "login-or-dc" => PipelineKind.LoginOrDc, "character-dashboard" => PipelineKind.CharacterDashboard,
        "entering-game-loading" => PipelineKind.EnteringGameLoading, "game" => PipelineKind.Game, "targeted" => PipelineKind.Targeted,
        _ => throw new InvalidDataException("Unknown Guard profile: " + id),
    };
    private static void AtomicWrite(string path, byte[] bytes)
    {
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try { File.WriteAllBytes(temp, bytes); File.Move(temp, path, true); }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
}
