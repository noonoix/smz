using System.Globalization;
using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Adds the root-only cycle contract and its canonical Pico adapters to a PlanExporter bundle.</summary>
public static class AutoCyclePlanBundle
{
    private static readonly string[] RuntimeFiles =
        { "plan_cycle.py", "cycle_runtime.py", "restart_windows.py", "auto_resume_boot.py",
          "resume_essentials_runtime.py" };

    public static IReadOnlyList<string> Export(string planPath, IList<StepNode> steps,
        AppSettings settings, int screenW, int screenH, string sourceName, string machine)
    {
        var runtimeDir = Path.Combine(AppContext.BaseDirectory, "portable-runtime");
        foreach (var name in RuntimeFiles)
            if (!File.Exists(Path.Combine(runtimeDir, name)))
                throw new IOException("فایل runtime چرخه پیدا نشد: " + name);

        var errors = ResumeEssentialsContract.Validate(steps);
        if (errors.Count > 0) throw new PlanExporter.PlanBlockedException(errors);

        // The old exporter still owns action lowering and recursive INCLUDE compilation.
        var written = PlanExporter.Export(planPath, steps, settings, screenW, screenH, sourceName, machine).ToList();
        var full = Path.GetFullPath(planPath);
        var dir = Path.GetDirectoryName(full) ?? throw new IOException("مسیر خروجی پلن نامعتبر است.");
        var decorated = DecorateRoot(File.ReadAllText(full), settings);
        var essential = ResumeEssentialsContract.Find(steps);
        var essentialsText = essential is null
            ? "ESSENTIALS|1\n" // overwrite any stale package from a previous export
            : PlanExporter.CompileOnce(new List<StepNode> { essential }, settings,
                screenW, screenH, sourceName + "#resume-essentials", machine).Text;
        var essentialsPath = Path.Combine(dir, "resume_essentials.txt");

        var payloads = new List<(string Path, byte[] Bytes)>
        {
            (full, new UTF8Encoding(false).GetBytes(decorated)),
            (essentialsPath, new UTF8Encoding(false).GetBytes(essentialsText)),
        };
        foreach (var name in RuntimeFiles)
            payloads.Add((Path.Combine(dir, name), File.ReadAllBytes(Path.Combine(runtimeDir, name))));
        PublishAtomically(payloads);
        written.Add(essentialsPath);
        written.AddRange(RuntimeFiles.Select(name => Path.Combine(dir, name)));
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static string DecorateRoot(string text, AppSettings settings)
    {
        var lines = text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n').ToList();
        if (lines.Count == 0 || lines[0] != "PLAN|2")
            throw new PlanExporter.PlanBlockedException(new[] { "PlanExporter BUG: خروجی Root با PLAN|2 شروع نشده است." });
        if (lines.Skip(1).Any(line => line.StartsWith("RUNFOR|", StringComparison.Ordinal)
                                   || line.StartsWith("AUTORESUME|", StringComparison.Ordinal)
                                   || line.StartsWith("POSTLAUNCH|", StringComparison.Ordinal)))
            throw new PlanExporter.PlanBlockedException(new[] { "PlanExporter BUG: directive چرخه در Root تکراری است." });

        var (restartMin, restartMax) = AppSettings.NormalizeMinuteRange(
            settings.RestartMinMinutes, settings.RestartMaxMinutes, 110, 130);
        var (resumeMin, resumeMax) = AppSettings.NormalizeMinuteRange(
            settings.AutoResumeMinMinutes, settings.AutoResumeMaxMinutes, 3, 5);
        var (launchBeforeMin, launchBeforeMax) = AppSettings.NormalizePositiveRange(
            settings.PostRestartLaunchBeforeMinSeconds, settings.PostRestartLaunchBeforeMaxSeconds, 1, 3);
        var (launchAfterMin, launchAfterMax) = AppSettings.NormalizePositiveRange(
            settings.PostRestartLaunchAfterMinSeconds, settings.PostRestartLaunchAfterMaxSeconds, 20, 40);
        var launchSlot = Math.Clamp(settings.PostRestartTaskbarSlot, 1, 9);
        var directives = new[]
        {
            "RUNFOR|" + (restartMin * 60).ToString(CultureInfo.InvariantCulture) + "," + (restartMax * 60).ToString(CultureInfo.InvariantCulture),
            "AUTORESUME|" + (settings.AutoResumeEnabled ? "1" : "0") + ","
                + (resumeMin * 60).ToString(CultureInfo.InvariantCulture) + ","
                + (resumeMax * 60).ToString(CultureInfo.InvariantCulture),
            "POSTLAUNCH|" + (settings.PostRestartLaunchEnabled ? "1" : "0") + ","
                + launchSlot.ToString(CultureInfo.InvariantCulture) + ","
                + launchBeforeMin.ToString(CultureInfo.InvariantCulture) + ","
                + launchBeforeMax.ToString(CultureInfo.InvariantCulture) + ","
                + launchAfterMin.ToString(CultureInfo.InvariantCulture) + ","
                + launchAfterMax.ToString(CultureInfo.InvariantCulture),
        };
        lines.InsertRange(1, directives);
        return string.Join("\n", lines);
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
