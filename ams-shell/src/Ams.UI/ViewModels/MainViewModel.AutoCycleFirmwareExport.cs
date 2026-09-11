using System.IO;
using System.Windows;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void ExportAutoCyclePicoFirmware()
    {
        var dlg = new Microsoft.Win32.SaveFileDialog
        {
            Filter = "Automatic-cycle firmware (code.py)|code.py",
            FileName = "code.py",
            Title = "خروجی firmware چرخه‌ی خودکار — درایو CIRCUITPY را انتخاب کن",
        };
        if (dlg.ShowDialog() != true) return;
        try
        {
            var mode = _settings.PlayRepeatMode;
            var seconds = mode == "timed"
                ? (int)(_settings.PlayRepeatUnit switch
                {
                    "second" => TimeSpan.FromSeconds(Math.Max(1, _settings.PlayRepeatValue)),
                    "hour" => TimeSpan.FromHours(Math.Max(1, _settings.PlayRepeatValue)),
                    _ => TimeSpan.FromMinutes(Math.Max(1, _settings.PlayRepeatValue)),
                }).TotalSeconds
                : 0;
            var written = AutoCycleFirmwareBundle.Export(dlg.FileName, Steps, Environment.MachineName,
                mode, Math.Max(1, _settings.PlayRepeatTimes), seconds, false);
            foreach (var file in written) Log("auto-cycle firmware: " + Path.GetFileName(file));
            MessageBox.Show(
                $"Firmware چرخه‌ی خودکار ساخته شد ({written.Count} فایل).\n"
                + "پس از Restart، برد ابتدا اتصال USB ویندوز را می‌بیند و سپس بازه‌ی Resume را صبر می‌کند.\n"
                + "فشردن GP4/Num Lock انتظار خودکار را لغو و شروع را دستی می‌کند.",
                "Export automatic-cycle firmware", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            Log("auto-cycle firmware export failed: " + ex.Message);
            MessageBox.Show("خروجی firmware چرخه ناموفق بود: " + ex.Message,
                "Export automatic-cycle firmware", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
