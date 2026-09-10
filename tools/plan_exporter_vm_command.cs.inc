    /// <summary>
    /// v0.9.65 — File → Export Pico Plan… (phase 2 of the portable line): compiles the open step
    /// tree into a portable plan.txt (PLAN|1, the gen-1 engine of firmware 0.9.64b) plus
    /// plan_engine.py and README-PLAN.md. Unsupported steps BLOCK the export with a per-step
    /// message in the serial log — nothing is silently skipped (project rule).
    /// </summary>
    [RelayCommand]
    private void ExportPicoPlan()
    {
        var dlg = new Microsoft.Win32.SaveFileDialog
        {
            Filter = "Pico portable plan (plan.txt)|plan.txt",
            FileName = "plan.txt",
            Title = "Export Pico plan — choose where plan.txt is written (then copy the files onto CIRCUITPY)",
        };
        if (dlg.ShowDialog() != true) return;
        try
        {
            var written = PlanExporter.Export(dlg.FileName, Steps, _settings,
                (int)SystemParameters.PrimaryScreenWidth, (int)SystemParameters.PrimaryScreenHeight,
                _currentFile is null ? "untitled" : Path.GetFileName(_currentFile), Environment.MachineName);
            foreach (var f in written) Log("pico plan: " + Path.GetFileName(f));
            Log($"pico plan: {written.Count} file(s) written — copy plan.txt + plan_engine.py onto CIRCUITPY (code.py comes from Export Pico Firmware)");
            System.Windows.MessageBox.Show($"پلن پیکو ساخته شد ({written.Count} فایل).\nplan.txt و plan_engine.py را در ریشه‌ی CIRCUITPY کپی کن (code.py از «Export Pico Firmware» می‌آید).\nراهنما در README-PLAN.md است.",
                "Export Pico plan", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (PlanExporter.PlanBlockedException bx)
        {
            Log($"pico plan export blocked ({bx.Errors.Count} problem(s)) — nothing written:");
            foreach (var e in bx.Errors) Log("  x " + e);
            System.Windows.MessageBox.Show($"اکسپورت پلن متوقف شد — {bx.Errors.Count} مورد روی PLAN|1 پشتیبانی نمی‌شود.\nجزئیات هر مورد در لاگ سریال هست (هیچ استپی بی‌صدا حذف نشد).",
                "Export Pico plan", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            Log("pico plan export failed: " + ex.Message);
            System.Windows.MessageBox.Show("خروجی پلن پیکو ناموفق بود: " + ex.Message,
                "Export Pico plan", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

