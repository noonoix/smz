using System.Security.Cryptography;
using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Publishes the known-good combined Guard bundle used by build 100.
///
/// The previous implementation called PicoFirmwareExporter, which produced the older
/// standalone-plan firmware and required /lib/adafruit_hid. That is a different runtime
/// from the combined Guard bundle and was the reason 101new could not boot on Pico.
/// Keep the two formats separate: this exporter copies the reviewed Guard runtime and
/// overlays only the plan/route files authored by the current workspace.
/// </summary>
public static class AutoCycleFirmwareBundle
{
    private static readonly string[] StaticBundleFiles =
    {
        "boot.py",
        "code.py",
        "combined_guard_runtime.py",
        "error_policy.py",
        "guard-calibration.json",
        "guard-transition.json",
        "guard_calibration_protocol.py",
        "guard_transition.py",
        "live_light_guard.py",
        "pico-calibration.json",
        "plan_engine.py",
        "README-FLASH.md",
    };

    private static readonly string[] GeneratedPlanFiles =
    {
        "plan.txt",
        "desktop_steps.txt",
        "restart_steps.txt",
        "login_or_dc_steps.txt",
        "dc_steps.txt",
        "character_dashboard_steps.txt",
        "entering_game_loading_steps.txt",
        "game_steps.txt",
        "targeted_steps.txt",
        "resumable_steps.txt",
    };

    private static readonly string[] LegacyCycleFiles =
    {
        "auto_resume_boot.py",
        "cycle_runtime.py",
        "launch_recovery.txt",
        "launch_steps.txt",
        "main_recovery.txt",
        "plan_cycle.py",
        "plan_motion.py",
        "plan_typing.py",
        "recovery_runtime.py",
        "restart_windows.py",
        "resume_essentials.txt",
        "resume_essentials_runtime.py",
    };

    // This is the 100-style manifest: all validated payloads except SHA256SUMS.txt.
    // It intentionally includes the dedicated DC route used by the current Guard policy.
    private static IEnumerable<string> ManifestFiles()
        => StaticBundleFiles
            .Concat(GeneratedPlanFiles)
            .OrderBy(name => name, StringComparer.Ordinal);

    public static IReadOnlyList<string> Export(
        string codePyPath,
        IEnumerable<StepNode> steps,
        string machine,
        string loopMode,
        int loopCount,
        int loopSeconds,
        bool keyboardOnArm)
    {
        _ = steps;
        _ = machine;
        _ = loopMode;
        _ = loopCount;
        _ = loopSeconds;
        _ = keyboardOnArm;

        var fullCodePath = Path.GetFullPath(codePyPath);
        var stagingDir = Path.GetDirectoryName(fullCodePath)
            ?? throw new IOException("مسیر خروجی firmware نامعتبر است.");
        var runtimeDir = Path.Combine(AppContext.BaseDirectory, "portable-runtime");

        foreach (var name in StaticBundleFiles)
        {
            var source = Path.Combine(runtimeDir, name);
            if (!File.Exists(source))
                throw new IOException("فایل Guard bundle پیدا نشد: " + name);
        }

        foreach (var name in GeneratedPlanFiles)
        {
            if (!File.Exists(Path.Combine(stagingDir, name)))
                throw new IOException("فایل مسیر تولید نشده است: " + name);
        }

        // Do not leave the 101new standalone/cycle files beside the combined Guard
        // runtime. Keeping a single reviewed inventory is important because code.py
        // validates the complete bundle before it starts.
        foreach (var name in LegacyCycleFiles)
        {
            var legacy = Path.Combine(stagingDir, name);
            if (File.Exists(legacy)) File.Delete(legacy);
        }

        foreach (var name in StaticBundleFiles)
        {
            var source = Path.Combine(runtimeDir, name);
            var destination = Path.Combine(stagingDir, name);
            File.Copy(source, destination, true);
        }

        var manifest = new StringBuilder();
        foreach (var name in ManifestFiles())
        {
            var path = Path.Combine(stagingDir, name);
            if (!File.Exists(path))
                throw new IOException("فایل Guard برای manifest موجود نیست: " + name);
            manifest.Append(HexSha256(path)).Append("  ").Append(name).Append('\n');
        }
        File.WriteAllText(Path.Combine(stagingDir, "SHA256SUMS.txt"), manifest.ToString(),
            new UTF8Encoding(false));

        return Directory.GetFiles(stagingDir, "*", SearchOption.TopDirectoryOnly)
            .Where(path => !path.EndsWith(".tmp", StringComparison.OrdinalIgnoreCase))
            .OrderBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    private static string HexSha256(string path)
    {
        using var stream = File.OpenRead(path);
        var digest = SHA256.HashData(stream);
        return Convert.ToHexString(digest).ToLowerInvariant();
    }
}
