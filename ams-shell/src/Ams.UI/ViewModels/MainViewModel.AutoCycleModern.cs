using System.IO;
using System.Windows;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;
using Forms = System.Windows.Forms;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    /// <summary>Copies the split-memory modern bundle; Golden 100 remains a separate export.</summary>
    [RelayCommand]
    private void ExportAutoCycleModern()
    {
        using var dialog = new Forms.FolderBrowserDialog
        {
            Description = "ریشهٔ درایو CIRCUITPY پیکو را برای Bundle مدرن انتخاب کن",
            UseDescriptionForTitle = true,
            ShowNewFolderButton = false,
        };
        if (dialog.ShowDialog() != Forms.DialogResult.OK) return;

        var targetRoot = dialog.SelectedPath;
        string? staging = null;
        try
        {
            staging = Path.Combine(Path.GetTempPath(), "ClassroomStudio-modern-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(staging);
            var files = ModernAutoCycleFirmwareBundle.Export(Path.Combine(staging, "code.py"))
                .OrderBy(path => Path.GetFileName(path).Equals("code.py", StringComparison.OrdinalIgnoreCase) ? 1 : 0)
                .ThenBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
                .ToArray();

            Directory.CreateDirectory(targetRoot);
            foreach (var source in files)
            {
                var destination = Path.Combine(targetRoot, Path.GetFileName(source));
                File.Copy(source, destination, true);
                Log("pico modern export: " + Path.GetFileName(source));
            }
            MessageBox.Show(
                $"Bundle مدرن split-memory ساخته و روی CIRCUITPY کپی شد ({files.Length} فایل).\n"
                + "این خروجی جایگزین Golden 100 نیست و برای ادامهٔ تست حافظه استفاده می‌شود.",
                "Modern Pico export", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            Log("pico modern export failed: " + ex.Message);
            MessageBox.Show("خروجی Bundle مدرن ناموفق بود: " + ex.Message,
                "Modern Pico export", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            if (staging is not null)
            {
                try { if (Directory.Exists(staging)) Directory.Delete(staging, true); }
                catch { }
            }
        }
    }
}