using System.IO;
using System.Windows;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    /// <summary>v0.9.67 — cycle-aware export entry point while the legacy File menu remains stable.</summary>
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
            var written = AutoCyclePlanBundle.Export(dlg.FileName, Steps, _settings,
                (int)SystemParameters.PrimaryScreenWidth, (int)SystemParameters.PrimaryScreenHeight,
                _currentFile ?? "untitled", Environment.MachineName);
            foreach (var file in written) Log("auto-cycle plan: " + Path.GetFileName(file));
            Log($"auto-cycle plan: {written.Count} file(s) written — Root owns the wall-clock deadline; INCLUDE plans inherit it");
            MessageBox.Show(
                $"بسته‌ی چرخه‌ی خودکار ساخته شد ({written.Count} فایل).\n"
                + "RUNFOR و AUTORESUME فقط در plan.txt اصلی نوشته شدند.\n"
                + "plan_cycle.py، cycle_runtime.py و restart_windows.py نیز کنار پلن قرار گرفتند.\n"
                + "همه‌ی فایل‌های خروجی را در ریشه‌ی CIRCUITPY نگه دار.",
                "Export automatic-cycle Pico plan", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (PlanExporter.PlanBlockedException bx)
        {
            Log($"auto-cycle export blocked ({bx.Errors.Count} problem(s)):");
            foreach (var error in bx.Errors) Log("  x " + error);
            MessageBox.Show(
                $"اکسپورت چرخه متوقف شد — {bx.Errors.Count} خطا. جزئیات در لاگ برنامه است.",
                "Export automatic-cycle Pico plan", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            Log("auto-cycle export failed: " + ex.Message);
            MessageBox.Show("خروجی چرخه‌ی خودکار ناموفق بود: " + ex.Message,
                "Export automatic-cycle Pico plan", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
