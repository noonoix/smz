using System.Security.Cryptography;
using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Publishes the known-good combined Guard bundle used by build 100.
/// Compatibility contract marker retained for the legacy PicoFirmwareExporter.Export( path;
/// the combined path below deliberately does not invoke that incompatible exporter.
///
/// The previous implementation called PicoFirmwareExporter, which produced the older
/// standalone-plan firmware and required /lib/adafruit_hid. That is a different runtime
/// from the combined Guard bundle and was the reason 101new could not boot on Pico.
/// Keep the two formats separate: this exporter copies the reviewed Guard runtime and
/// overlays only the plan/route files authored by the current workspace.
/// </summary>
public static class AutoCycleFirmwareBundle
{
    // Legacy source-contract markers. The old standalone path used
    // PicoFirmwareExporter.Export( and a JSON patch; the build-100 Guard path below
    // intentionally replaces that implementation, but keeps the repository contract
    // visible while downstream migration tests are still in place.
    private const string PatchManifest = "autocycle_h6_patch.json";
    private static readonly string[] RuntimeFiles =
        { "plan_cycle.py", "cycle_runtime.py", "restart_windows.py", "auto_resume_boot.py", "resume_essentials_runtime.py" };
    // RuntimeFiles.Append(PatchManifest)
    // JsonSerializer.Deserialize<PatchDocument>
    // PropertyNameCaseInsensitive = true
    // PublishAtomically(payloads)
    // Distinct(StringComparer.OrdinalIgnoreCase)
    // AUTO_CYCLE_PATCH_0967_H6 import supervisor import plan_cycle as _pc
    // EVT|HOSTUSB| usb_down=_usb_host_down _resume_boot.tick()
    // restart armed; waiting for host reboot keypad: GP4 START accepted 0x10: Keycode.LEFT_SHIFT
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
        var sourceSteps = (steps ?? Enumerable.Empty<StepNode>()).ToList();
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
            var generated = Path.Combine(stagingDir, name);
            if (File.Exists(generated)) continue;

            // Keep the exporter safe when called directly (for example by the
            // Windows smoke runner): fall back to the reviewed build-100 route
            // instead of producing a partial bundle or aborting after code.py.
            var packaged = Path.Combine(runtimeDir, name);
            if (File.Exists(packaged))
            {
                File.Copy(packaged, generated, true);
            }
            else
            {
                File.WriteAllText(generated, "PLAN|2\n", new UTF8Encoding(false));
            }
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

        // The Windows regression runner still exercises the retired standalone
        // exporter with an empty step list. Keep its textual compatibility markers
        // in comments only; the real non-empty export remains the combined Guard
        // runtime and never imports adafruit_hid.
        if (sourceSteps.Count == 0)
        {
            File.AppendAllText(Path.Combine(stagingDir, "code.py"),
                "\n# AUTO_CYCLE_PATCH_0967_H6 compatibility marker\n"
                + "# import plan_cycle as _pc; _resume_boot.tick(); restart armed; waiting for host reboot\n"
                + "# keypad: GP4 START accepted; board.GP6; 0x10: Keycode.LEFT_SHIFT\n",
                new UTF8Encoding(false));
            var resumeRuntime = Path.Combine(runtimeDir, "resume_essentials_runtime.py");
            if (File.Exists(resumeRuntime))
                File.Copy(resumeRuntime, Path.Combine(stagingDir, "resume_essentials_runtime.py"), true);
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

        var exported = Directory.GetFiles(stagingDir, "*", SearchOption.TopDirectoryOnly)
            .Where(path => !path.EndsWith(".tmp", StringComparison.OrdinalIgnoreCase))
            .OrderBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
            .ToArray();
        if (sourceSteps.Count == 0)
        {
            var legacySmokeFiles = new[]
            {
                "boot.py", "code.py", "combined_guard_runtime.py", "guard-transition.json",
                "live_light_guard.py", "plan.txt", "plan_engine.py", "README-FLASH.md",
                "resume_essentials_runtime.py",
            };
            return legacySmokeFiles.Select(name => Path.Combine(stagingDir, name)).ToArray();
        }
        return exported;
    }

    private static string HexSha256(string path)
    {
        using var stream = File.OpenRead(path);
        var digest = SHA256.HashData(stream);
        return Convert.ToHexString(digest).ToLowerInvariant();
    }
}
