using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Windows;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void ExportCombinedPortableGuard()
    {
        var dlg = new Microsoft.Win32.SaveFileDialog
        {
            Filter = "Complete Pico Guard bundle (plan.txt)|plan.txt",
            FileName = "plan.txt",
            Title = "ساخت بسته کامل چرخه + Macro + Guard — پوشه CIRCUITPY را انتخاب کن",
        };
        if (dlg.ShowDialog() != true) return;

        try
        {
            var workspace = CapturePipelineWorkspaceForExport();
            var written = PortableGuardBundle.Export(
                dlg.FileName,
                workspace,
                LightStateProfiles.ToArray(),
                _settings,
                (int)SystemParameters.PrimaryScreenWidth,
                (int)SystemParameters.PrimaryScreenHeight,
                _currentFile ?? "untitled",
                Environment.MachineName).ToList();

            // One source of truth: cycle directives are embedded in the same root plan
            // that carries the Guard routes. Separate plan/firmware exporters are hidden,
            // so two exports cannot overwrite each other.
            var directory = Path.GetDirectoryName(Path.GetFullPath(dlg.FileName))
                ?? throw new IOException("مسیر خروجی bundle نامعتبر است.");
            var planPath = Path.Combine(directory, "plan.txt");
            var decoratedPlan = AutoCyclePlanBundle.DecorateRoot(
                File.ReadAllText(planPath), _settings);
            WriteAtomic(planPath, new UTF8Encoding(false).GetBytes(decoratedPlan));

            // plan.txt changed after bundle generation; rebuild hashes so the board
            // never receives a stale manifest.
            var hashPath = Path.Combine(directory, "SHA256SUMS.txt");
            var hashFiles = written
                .Where(path => !string.Equals(Path.GetFileName(path), "SHA256SUMS.txt", StringComparison.OrdinalIgnoreCase))
                .Where(File.Exists)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
                .ToArray();
            var hashes = string.Join(Environment.NewLine, hashFiles.Select(path =>
                Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant()
                + "  " + Path.GetFileName(path))) + Environment.NewLine;
            WriteAtomic(hashPath, new UTF8Encoding(false).GetBytes(hashes));

            foreach (var file in written) Log("complete Guard bundle: " + Path.GetFileName(file));
            Log("complete Guard bundle: AutoCycle directives embedded in plan.txt; manifest rebuilt");
            MessageBox.Show(
                $"بستهٔ کامل ساخته شد ({written.Count} فایل).\n\n"
                + "همه‌چیز در یک خروجی قرار گرفت:\n"
                + "• تنظیمات چرخهٔ خودکار و Restart/Resume\n"
                + "• تمام routeهای ماکرو و Recovery\n"
                + "• Guard، کالیبراسیون و runtime\n"
                + "• manifest بازسازی‌شده با hashهای نهایی\n\n"
                + "فایل‌های plan جداگانه یا firmware جداگانه تولید نمی‌شوند.",
                "Complete Pico Guard bundle", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (PlanExporter.PlanBlockedException bx)
        {
            Log($"complete Guard export blocked ({bx.Errors.Count} problem(s)) — nothing written:");
            foreach (var error in bx.Errors) Log("  x " + error);
            MessageBox.Show(
                $"اکسپورت بستهٔ کامل متوقف شد — {bx.Errors.Count} خطای Step. جزئیات در لاگ است.",
                "Complete Pico Guard bundle", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            Log("complete Guard export failed: " + ex.Message);
            MessageBox.Show("ساخت بستهٔ کامل ناموفق بود: " + ex.Message,
                "Complete Pico Guard bundle", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private static void WriteAtomic(string path, byte[] bytes)
    {
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllBytes(temporary, bytes);
            File.Move(temporary, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    // ExportAutoCyclePicoPlan and ExportAutoCyclePicoFirmware remain available to
    // older serialized commands, but their UI hooks are intentionally disabled.
}
