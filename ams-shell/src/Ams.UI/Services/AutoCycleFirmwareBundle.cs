using System.Text;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Applies the byte-verified AutoCycle/HostUSB patch to the hardware-proven h6 Pico
/// export and publishes the complete runtime as one rollback-safe transaction.
/// </summary>
public static class AutoCycleFirmwareBundle
{
    private const string PatchManifest = "autocycle_h6_patch.json";
    private static readonly string[] RuntimeFiles =
    {
        "plan_cycle.py", "cycle_runtime.py", "restart_windows.py",
        "auto_resume_boot.py", "resume_essentials_runtime.py",
    };

    public static IReadOnlyList<string> Export(string codePyPath, IEnumerable<StepNode> steps,
        string machine, string loopMode, int loopCount, int loopSeconds, bool keyboardOnArm)
    {
        var runtimeDir = Path.Combine(AppContext.BaseDirectory, "portable-runtime");
        foreach (var name in RuntimeFiles.Append(PatchManifest))
            if (!File.Exists(Path.Combine(runtimeDir, name)))
                throw new IOException("فایل runtime چرخه پیدا نشد: " + name);

        var written = PicoFirmwareExporter.Export(codePyPath, steps, machine,
            loopMode, loopCount, loopSeconds, keyboardOnArm).ToList();
        var full = Path.GetFullPath(codePyPath);
        var dir = Path.GetDirectoryName(full) ?? throw new IOException("مسیر firmware نامعتبر است.");
        var patched = PatchCode(File.ReadAllText(full), Path.Combine(runtimeDir, PatchManifest));

        var payloads = new List<(string Path, byte[] Bytes)>
        {
            (full, new UTF8Encoding(false).GetBytes(patched)),
        };
        foreach (var name in RuntimeFiles)
            payloads.Add((Path.Combine(dir, name), File.ReadAllBytes(Path.Combine(runtimeDir, name))));
        PublishAtomically(payloads);
        written.AddRange(RuntimeFiles.Select(name => Path.Combine(dir, name)));
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static string PatchCode(string code, string manifestPath)
    {
        // PicoFirmwareExporter is compiled from a raw string. On Windows its generated
        // code.py can carry CRLF while the canonical JSON manifest intentionally uses LF.
        // Normalize before byte-unique anchor matching and publish one stable LF artifact.
        code = code.Replace("\r\n", "\n").Replace('\r', '\n');
        var manifest = JsonSerializer.Deserialize<PatchDocument>(
            File.ReadAllText(manifestPath),
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
            ?? throw new InvalidDataException("manifest چرخه قابل خواندن نیست.");
        if (manifest.Version != 1 || manifest.Edits.Count == 0)
            throw new InvalidDataException("نسخه یا محتوای manifest چرخه معتبر نیست.");
        if (!code.Contains(manifest.Baseline, StringComparison.Ordinal))
            throw new InvalidDataException("Firmware پایه h6 مورد انتظار پیدا نشد: " + manifest.Baseline);

        foreach (var edit in manifest.Edits)
            code = ReplaceOnce(code, edit.Old, edit.New);

        foreach (var marker in RequiredMarkers)
            if (!code.Contains(marker, StringComparison.Ordinal))
                throw new InvalidDataException("پست‌کاندیشن Firmware چرخه پیدا نشد: " + marker);
        return code;
    }

    private static readonly string[] RequiredMarkers =
    {
        "AUTO_CYCLE_PATCH_0967_H6",
        "import supervisor",
        "import plan_cycle as _pc",
        "from auto_resume_boot import AutoResumeBoot",
        "EVT|HOSTUSB|",
        "usb_down=_usb_host_down",
        "_resume_boot.tick()",
        "keypad: GP4 START accepted",
        "0x10: Keycode.LEFT_SHIFT",
    };

    private static string ReplaceOnce(string text, string oldText, string newText)
    {
        if (string.IsNullOrEmpty(oldText))
            throw new InvalidDataException("anchor خالی در manifest چرخه.");
        var first = text.IndexOf(oldText, StringComparison.Ordinal);
        if (first < 0 || text.IndexOf(oldText, first + oldText.Length, StringComparison.Ordinal) >= 0)
            throw new InvalidDataException("قالب firmware با قرارداد چرخه همگام نیست: "
                                           + oldText.Split('\n')[0]);
        return text[..first] + newText + text[(first + oldText.Length)..];
    }

    private sealed class PatchDocument
    {
        public int Version { get; set; }
        public string Baseline { get; set; } = "";
        public List<PatchEdit> Edits { get; set; } = new();
    }

    private sealed class PatchEdit
    {
        public string Old { get; set; } = "";
        public string New { get; set; } = "";
    }

    private static void PublishAtomically(IReadOnlyList<(string Path, byte[] Bytes)> payloads)
    {
        var tx = Guid.NewGuid().ToString("N");
        var temps = payloads.Select(p => p.Path + "." + tx + ".tmp").ToArray();
        var backups = payloads.Select(p => p.Path + "." + tx + ".bak").ToArray();
        var published = new List<int>();
        try
        {
            for (var i = 0; i < payloads.Count; i++) File.WriteAllBytes(temps[i], payloads[i].Bytes);
            for (var i = 0; i < payloads.Count; i++)
            {
                if (File.Exists(payloads[i].Path)) File.Move(payloads[i].Path, backups[i]);
                File.Move(temps[i], payloads[i].Path);
                published.Add(i);
            }
            foreach (var backup in backups) if (File.Exists(backup)) File.Delete(backup);
        }
        catch
        {
            foreach (var i in published.AsEnumerable().Reverse())
                if (File.Exists(payloads[i].Path)) File.Delete(payloads[i].Path);
            for (var i = 0; i < payloads.Count; i++)
                if (File.Exists(backups[i])) File.Move(backups[i], payloads[i].Path, true);
            throw;
        }
        finally
        {
            foreach (var file in temps.Concat(backups)) if (File.Exists(file)) File.Delete(file);
        }
    }
}
