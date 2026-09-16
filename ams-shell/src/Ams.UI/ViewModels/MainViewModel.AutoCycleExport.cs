using System.IO;
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
            Filter = "Combined Pico + Arduino Guard bundle (plan.txt)|plan.txt",
            FileName = "plan.txt",
            Title = "خروجی Combined Portable Guard — پوشه‌ی CIRCUITPY را انتخاب کن",
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
                Environment.MachineName);

            foreach (var file in written) Log("combined Guard export: " + Path.GetFileName(file));
            Log($"combined Pico + Arduino arm bundle: {written.Count} file(s) written; CIRCUITPY is the runtime source of truth");
            MessageBox.Show(
                $"بسته‌ی Combined Pico + Arduino arm ساخته شد ({written.Count} فایل).\n"
                + "plan.txt ورودی STATELOOP است؛ هفت فایل route، manifest، calibration و runtimeها هم کنار آن نوشته شدند.\n"
                + "این خروجی فقط برای بررسی و کپی دستی روی CIRCUITPY است؛ هنوز نصب سخت‌افزار، merge یا پذیرش تولید انجام نشده است.",
                "Export Combined Portable Guard", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (PlanExporter.PlanBlockedException bx)
        {
            Log($"combined Guard export blocked ({bx.Errors.Count} problem(s)) — nothing written:");
            foreach (var error in bx.Errors) Log("  x " + error);
            MessageBox.Show(
                $"اکسپورت Combined Guard متوقف شد — {bx.Errors.Count} خطای Step. جزئیات در لاگ است.",
                "Export Combined Portable Guard", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            Log("combined Guard export failed: " + ex.Message);
            MessageBox.Show("خروجی Combined Guard ناموفق بود: " + ex.Message,
                "Export Combined Portable Guard", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    [RelayCommand]
    private void ExportAutoCyclePicoPlan()
    {
        var dlg = new Microsoft.Win32.SaveFileDialog
        {
            Filter = "Pico automatic-cycle plan (plan.txt)|plan.txt",
            FileName = "plan.txt",
            Title = "خروجی چرخه‌ی خودکار پیکو — پوشه‌ی CIRCUITPY را انتخاب کن",
        };
        if (dlg.ShowDialog() != true) return;
        try
        {
            var workspace = CapturePipelineWorkspaceForExport();
            var written = PipelinePlanBundle.Export(dlg.FileName, workspace, _settings,
                (int)SystemParameters.PrimaryScreenWidth, (int)SystemParameters.PrimaryScreenHeight,
                _currentFile ?? "untitled", Environment.MachineName);
            foreach (var file in written) Log("auto-cycle plan: " + Path.GetFileName(file));
            Log($"auto-cycle pipeline: {written.Count} file(s) written; Main owns cycle directives");
            MessageBox.Show(
                $"بسته‌ی Pipeline ساخته شد ({written.Count} فایل).\n"
                + "Launch، Main، دو Recovery و Resume Essentials به فایل‌های مستقل PLAN|2 تبدیل شدند.\n"
                + "RUNFOR و AUTORESUME فقط در plan.txt اصلی نوشته شدند.\n"
                + "همه‌ی فایل‌ها را در ریشه‌ی CIRCUITPY نگه دار.",
                "Export AutoCycle Pipeline", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (PlanExporter.PlanBlockedException bx)
        {
            Log($"auto-cycle export blocked ({bx.Errors.Count} problem(s)):");
            foreach (var error in bx.Errors) Log("  x " + error);
            MessageBox.Show($"اکسپورت Pipeline متوقف شد — {bx.Errors.Count} خطا. جزئیات در لاگ است.",
                "Export AutoCycle Pipeline", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            Log("auto-cycle export failed: " + ex.Message);
            MessageBox.Show("خروجی Pipeline ناموفق بود: " + ex.Message,
                "Export AutoCycle Pipeline", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
