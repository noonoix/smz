// v0.9.50 — Board preparation window (the AMS USB Studio tool ported into Classroom
// Studio). Four tabs: build a Caterina HEX with a custom USB identity, install the board
// definition into the Arduino IDE, flash via ISP with the bundled tools\isp_flash.py,
// and the read-only board checkup. All pure logic lives in Services\Board*.cs so
// TestRunner step 50 covers it; this file is only wiring and dialogs.
// Golden rule honoured: every WPF/WinForms-shared name is fully qualified.
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Ams.UI.Services;

namespace Ams.UI.Views;

public partial class BoardPrepWindow : Window
{
    /// <summary>Persisted next to the exe as board-prep-settings.json (same convention
    /// as ams-settings.json).</summary>
    private sealed class Settings
    {
        public string IdentityKey { get; set; } = "microchip";
        public string Serial { get; set; } = "AMS-00000000";
        public string Prefix { get; set; } = "AMS";
        public string Count { get; set; } = "1";
        public bool UseCustomVp { get; set; }
        public string CustomVid { get; set; } = "0x1D50";
        public string CustomPid { get; set; } = "0x615E";
        public string CustomProduct { get; set; } = "";
        public string CustomManuf { get; set; } = "";
        public string CaterinaPath { get; set; } = "";
        public string OutputDir { get; set; } = "";
        public bool TargetSketchbook { get; set; } = true;
        public string IdePath { get; set; } = "";
        public string FlashHex { get; set; } = "";
        public string FlashPort { get; set; } = "";
        public bool CheckOnly { get; set; } = true; = true;
        public bool Erase { get; set; } = false;
        public bool FixFuses { get; set; }
    }

    private readonly Settings _s;
    private readonly string _settingsPath;
    // Field initializers run before InitializeComponent, so XAML-assigned IsChecked/
    // SelectionChanged events during InitializeComponent are safely ignored.
    private bool _loading = true;
    private bool _flashRunning;
    private int _step = 1;   // v0.9.52 - wizard position (1..4)
    private bool _syncingSpecs;   // v0.9.54 - auto-fill must not look like a user edit
    private List<BoardCheckupService.PortInfo> _lastScan = new();   // v0.9.54 - last scan, re-rendered on demand

    public BoardPrepWindow()
    {
        InitializeComponent();
        InitializeUsbUpdatePanel();

        _settingsPath = Path.Combine(AppContext.BaseDirectory, "board-prep-settings.json");
        _s = LoadSettings();

        CmbIdentity.ItemsSource = BoardHexService.DeviceModes;

        TxtSerial.Text = _s.Serial;
        TxtPrefix.Text = _s.Prefix;
        TxtCount.Text = _s.Count;
        ChkCustom.IsChecked = _s.UseCustomVp;
        GridAdvanced.Visibility = _s.UseCustomVp ? Visibility.Visible : Visibility.Collapsed;
        TxtVid.Text = _s.CustomVid;
        TxtPid.Text = _s.CustomPid;
        TxtProduct.Text = _s.CustomProduct;
        TxtManuf.Text = _s.CustomManuf;
        TxtCaterina.Text = _s.CaterinaPath.Length > 0 ? _s.CaterinaPath
            : BundledAssets.Find(AppContext.BaseDirectory, "caterina", "Caterina.hex") ?? "";
        TxtOutputDir.Text = _s.OutputDir.Length > 0 ? _s.OutputDir
            : Path.Combine(AppContext.BaseDirectory, "patches");
        RadioSketchbook.IsChecked = _s.TargetSketchbook;
        RadioBoardsTxt.IsChecked = !_s.TargetSketchbook;
        TxtIdePath.Text = _s.IdePath;
        ChkCheckOnly.IsChecked = _s.CheckOnly;
        ChkErase.IsChecked = _s.Erase;
        ChkFixFuses.IsChecked = _s.FixFuses;
        CmbHex.Text = _s.FlashHex;
        CmbFlashPort.Text = _s.FlashPort;
        TabHex.IsChecked = true;

        CmbIdentity.SelectedItem = BoardHexService.ModeFor(_s.IdentityKey);
        _loading = false;
        // v0.9.54 - blank advanced boxes (first run, or a saved identity with no overrides)
        // start from the selected device's researched defaults instead of staying empty.
        var d0 = BoardHexService.DefaultsFor(CurrentIdentity.Key);
        if (TxtVid.Text.Trim().Length == 0) TxtVid.Text = d0.BootVid;
        if (TxtPid.Text.Trim().Length == 0) TxtPid.Text = d0.BootPid;
        if (TxtProduct.Text.Trim().Length == 0) TxtProduct.Text = d0.Product;
        if (TxtManuf.Text.Trim().Length == 0) TxtManuf.Text = d0.Manufacturer;
        FillBoardSpecFields();
        if (TxtIdePath.Text.Length == 0) TxtIdePath.Text = BoardsTxtService.DetectSketchbook();
        SyncIdeModeUi();
        RefreshHexList();
        RefreshFlashPorts();
        UpdatePreview();
        UpdateManualCmd();
        SyncWizardNav();
        Log("چهار قدم پشت سر هم: ۱ ساخت HEX ← ۲ نصب در IDE ← ۳ فلش ISP ← ۴ چکاپ. با دکمه‌ی «قدم بعدی» جلو برو.");
    }

    // ───────────────────────────── shared helpers ─────────────────────────────

    private void Log(string msg)
    {
        TxtLog.AppendText(msg + Environment.NewLine);
        TxtLog.ScrollToEnd();
    }

    private void SetStatus(string msg) => TxtStatus.Text = msg;

    private void ShowPanel(FrameworkElement panel, System.Windows.Controls.Primitives.ToggleButton tab)
    {
        if (_loading) return;
        PanelHex.Visibility = Visibility.Collapsed;
        PanelIde.Visibility = Visibility.Collapsed;
        PanelFlash.Visibility = Visibility.Collapsed;
        PanelCheckup.Visibility = Visibility.Collapsed;
        panel.Visibility = Visibility.Visible;
        TabHex.IsChecked = tab == TabHex;
        TabIde.IsChecked = tab == TabIde;
        TabFlash.IsChecked = tab == TabFlash;
        TabCheckup.IsChecked = tab == TabCheckup;
        _step = tab == TabHex ? 1 : tab == TabIde ? 2 : tab == TabFlash ? 3 : 4;
        SyncWizardNav();
    }

    // ── v0.9.52: wizard navigation. The four tabs are numbered steps and the shared
    // navigator below the panels always says where you are and what comes next. ──

    /// <summary>Short Persian description of each step, shown in the navigator.</summary>
    internal static string StepHint(int step) => step switch
    {
        1 => "قدم ۱ از ۴ · ساخت HEX — هویت دستگاه، سریال و مشخصات برد فقط همین‌جا وارد می‌شود",
        2 => "قدم ۲ از ۴ · نصب در IDE — همان مشخصات قدم ۱ خودکار اینجاست؛ فقط محل نصب را تأیید کن",
        3 => "قدم ۳ از ۴ · فلش ISP — برد پروگرمر با شش سیم به برد مقصد، و خودش با USB به کامپیوتر",
        _ => "قدم ۴ از ۴ · چکاپ برد — فقط می‌خواند و چیزی روی برد نمی‌نویسد",
    };

    /// <summary>Clamps a step number to the wizard range.</summary>
    internal static int ClampStep(int step) => step < 1 ? 1 : step > 4 ? 4 : step;

    private void SyncWizardNav()
    {
        if (TxtStepHint is null) return;
        TxtStepHint.Text = StepHint(_step);
        BtnPrevStep.IsEnabled = _step > 1;
        BtnNextStep.IsEnabled = _step < 4;
    }

    private void GoStep(int step)
    {
        step = ClampStep(step);
        switch (step)
        {
            case 1: ShowPanel(PanelHex, TabHex); break;
            case 2: ShowPanel(PanelIde, TabIde); break;
            case 3: ShowPanel(PanelFlash, TabFlash); break;
            default: ShowPanel(PanelCheckup, TabCheckup); break;
        }
    }

    private void BtnNextStep_Click(object sender, RoutedEventArgs e) => GoStep(_step + 1);

    private void BtnPrevStep_Click(object sender, RoutedEventArgs e) => GoStep(_step - 1);

    private void TabHex_Click(object sender, RoutedEventArgs e) => ShowPanel(PanelHex, TabHex);
    private void TabIde_Click(object sender, RoutedEventArgs e) => ShowPanel(PanelIde, TabIde);
    private void TabFlash_Click(object sender, RoutedEventArgs e) => ShowPanel(PanelFlash, TabFlash);
    private void TabCheckup_Click(object sender, RoutedEventArgs e) => ShowPanel(PanelCheckup, TabCheckup);

    private BoardHexService.DeviceMode CurrentIdentity
        => CmbIdentity.SelectedItem as BoardHexService.DeviceMode ?? BoardHexService.DeviceModes[0];

    private Settings LoadSettings()
    {
        try
        {
            if (File.Exists(_settingsPath))
                return JsonSerializer.Deserialize<Settings>(File.ReadAllText(_settingsPath)) ?? new Settings();
        }
        catch { /* a corrupt settings file must never block the window */ }
        return new Settings();
    }

    private void CollectSettings()
    {
        _s.IdentityKey = CurrentIdentity.Key;
        _s.Serial = TxtSerial.Text;
        _s.Prefix = TxtPrefix.Text;
        _s.Count = TxtCount.Text;
        _s.UseCustomVp = ChkCustom.IsChecked == true;
        _s.CustomVid = TxtVid.Text;
        _s.CustomPid = TxtPid.Text;
        _s.CustomProduct = TxtProduct.Text;
        _s.CustomManuf = TxtManuf.Text;
        _s.CaterinaPath = TxtCaterina.Text;
        _s.OutputDir = TxtOutputDir.Text;
        _s.TargetSketchbook = RadioSketchbook.IsChecked == true;
        _s.IdePath = TxtIdePath.Text;
        _s.FlashHex = CmbHex.Text;
        _s.FlashPort = CmbFlashPort.Text;
        _s.CheckOnly = ChkCheckOnly.IsChecked == true;
        _s.Erase = ChkErase.IsChecked == true;
        _s.FixFuses = ChkFixFuses.IsChecked == true;
    }

    private void SaveSettings()
    {
        try
        {
            File.WriteAllText(_settingsPath,
                JsonSerializer.Serialize(_s, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch { /* settings are a convenience, never a failure */ }
    }

    protected override void OnClosed(EventArgs e)
    {
        CollectSettings();
        SaveSettings();
        base.OnClosed(e);
    }

    private void ShowError(string title, Exception ex)
        => System.Windows.MessageBox.Show(this, ex.Message, title,
            MessageBoxButton.OK, MessageBoxImage.Warning);

    // ───────────────────────────── tab 1: build HEX ─────────────────────────────

    /// <summary>Mirrors the original tool's _resolve_identity: the preset supplies class
    /// and names; "none" leaves the device identity untouched (serial-only patch); the
    /// advanced VID/PID override wins when checked; non-empty custom names always win.</summary>
    private (int? Vid, int? Pid, int Cls, int Sub, int Proto, string? Product, string? Manuf) ResolveIdentityConfig()
    {
        var preset = CurrentIdentity;
        int? vid = null, pid = null;
        string? product = null, manuf = null;
        if (preset.Key != "none")
        {
            vid = preset.Vid;
            pid = preset.Pid;
            product = preset.Product;
            manuf = preset.Manufacturer;
        }
        if (ChkCustom.IsChecked == true)
        {
            vid = BoardHexService.ParseVidPid(TxtVid.Text, "VID");
            pid = BoardHexService.ParseVidPid(TxtPid.Text, "PID");
        }
        var cp = BoardHexService.ValidateUsbString(TxtProduct.Text, "نام محصول");
        var cm = BoardHexService.ValidateUsbString(TxtManuf.Text, "سازنده");
        if (cp.Length > 0) product = cp;
        if (cm.Length > 0) manuf = cm;
        return (vid, pid, preset.ClassType, preset.Subclass, preset.Protocol, product, manuf);
    }

    private void BtnRandom_Click(object sender, RoutedEventArgs e)
    {
        var prefix = TxtPrefix.Text.Trim();
        TxtSerial.Text = BoardHexService.GenerateRandomSerial(prefix.Length > 0 ? prefix : "AMS");
    }

    private void BtnBrowseCaterina_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "Caterina HEX|Caterina*.hex|HEX files|*.hex" };
        if (dlg.ShowDialog(this) == true) TxtCaterina.Text = dlg.FileName;
    }

    private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
    {
        using var dlg = new System.Windows.Forms.FolderBrowserDialog { SelectedPath = TxtOutputDir.Text };
        if (dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK) TxtOutputDir.Text = dlg.SelectedPath;
    }

    private async void BtnGenerate_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (!int.TryParse(TxtCount.Text, out int count) || count < 1 || count > 500)
                throw new ArgumentException("تعداد باید یک عدد بین ۱ تا ۵۰۰ باشد");
            var serials = new List<string>();
            if (count == 1)
            {
                serials.Add(BoardHexService.ValidateSerial(TxtSerial.Text));
            }
            else
            {
                var prefix = TxtPrefix.Text.Trim();
                if (prefix.Length == 0) prefix = "AMS";
                for (int i = 0; i < count; i++) serials.Add(BoardHexService.GenerateRandomSerial(prefix));
            }
            var cfg = ResolveIdentityConfig();
            var caterina = TxtCaterina.Text.Trim();
            if (!File.Exists(caterina))
                throw new FileNotFoundException("Caterina.hex پیدا نشد — از کارت «مسیرها» مسیر درست را انتخاب کن.");
            var outDir = TxtOutputDir.Text.Trim();
            if (outDir.Length == 0) throw new ArgumentException("پوشه‌ی خروجی خالی است.");

            CollectSettings();
            SaveSettings();
            BtnGenerate.IsEnabled = false;
            try
            {
                var result = await Task.Run(() =>
                {
                    Directory.CreateDirectory(outDir);
                    var flash = BoardHexService.ParseHex(caterina);
                    var lines = new List<string>();
                    int curVid = flash[BoardHexService.DeviceDescOffset + 8] | (flash[BoardHexService.DeviceDescOffset + 9] << 8);
                    int curPid = flash[BoardHexService.DeviceDescOffset + 10] | (flash[BoardHexService.DeviceDescOffset + 11] << 8);
                    lines.Add($"خواندن {Path.GetFileName(caterina)} …");
                    lines.Add($"هویت فعلی فایل: VID 0x{curVid:X4}  PID 0x{curPid:X4}");
                    lines.Add(cfg.Vid is not null
                        ? $"هویت جدید: VID 0x{cfg.Vid:X4}  PID 0x{cfg.Pid:X4}  class 0x{cfg.Cls:X2}"
                        : "هویت دستگاه بدون تغییر می‌ماند (فقط سریال پچ می‌شود)");
                    int okCount = 0, errCount = 0;
                    foreach (var serial in serials)
                    {
                        try
                        {
                            var patched = BoardHexService.PatchHex(flash, serial, cfg.Vid, cfg.Pid,
                                cfg.Cls, cfg.Sub, cfg.Proto, cfg.Product, cfg.Manuf);
                            File.WriteAllText(Path.Combine(outDir, $"Caterina-{serial}.hex"),
                                BoardHexService.ToHex(patched), Encoding.ASCII);
                            lines.Add($"  ✓ Caterina-{serial}.hex");
                            okCount++;
                        }
                        catch (Exception ex)
                        {
                            lines.Add($"  ✗ {serial}: {ex.Message}");
                            errCount++;
                        }
                    }
                    return (lines, okCount, errCount);
                });
                foreach (var l in result.lines) Log(l);
                Log($"نتیجه: {result.okCount} فایل ساخته شد" + (result.errCount > 0 ? $"، {result.errCount} خطا" : ""));
                Log($"پوشه: {outDir}");
                SetStatus($"تکمیل شد — {result.okCount} فایل ساخته شد؛ قدم بعد: تب «فلش ISP»");
                RefreshHexList();
            }
            finally { BtnGenerate.IsEnabled = true; }
        }
        catch (Exception ex) { ShowError("خطا در ورودی", ex); }
    }

    // ───────────────────────────── tab 2: install in the IDE ─────────────────────────────

    /// <summary>Board numbers for the IDE block: the identity's VID + bootloader PID is the
    /// preset PID (or the custom one); the application PID is bootloader + 1 — the same
    /// convention the original tool used (boot 0x…0A / app 0x…0B, boot 0x615E / app 0x615F).</summary>
    private (string BootVid, string BootPid, string AppPid, string Product, string Manuf) ResolveBoardNumbers()
    {
        var preset = CurrentIdentity;
        int vid = preset.Vid, pid = preset.Pid;
        string product = preset.Product, manuf = preset.Manufacturer;
        if (ChkCustom.IsChecked == true)
        {
            vid = BoardHexService.ParseVidPid(TxtVid.Text, "VID");
            pid = BoardHexService.ParseVidPid(TxtPid.Text, "PID");
        }
        if (TxtProduct.Text.Trim().Length > 0) product = TxtProduct.Text.Trim();
        if (TxtManuf.Text.Trim().Length > 0) manuf = TxtManuf.Text.Trim();
        return ($"0x{vid:X4}", $"0x{pid:X4}", $"0x{pid + 1:X4}", product, manuf);
    }

    private void UpdatePreview()
    {
        if (_loading || TxtPreview is null) return;
        try
        {
            var s = BoardSpecsFromUi();
            var specs = $"مشخصات برد: شناسه «{s.BoardId}» · نام «{s.BoardName}» · بوت‌لودر {s.BootVid}:{s.BootPid} · اپلیکیشن PID {s.AppPid} · محصول «{s.Product}» · سازنده «{s.Manuf}»";
            if (TxtBoardSpecs is not null) TxtBoardSpecs.Text = specs;
            if (TxtBoardSpecs1 is not null) TxtBoardSpecs1.Text = specs;
            TxtPreview.Text = BoardsTxtService.BuildBoardBlock(boardId: s.BoardId, name: s.BoardName,
                bootVid: s.BootVid, bootPid: s.BootPid, appPid: s.AppPid, product: s.Product,
                manufacturer: s.Manuf, crossCore: RadioSketchbook.IsChecked == true);
        }
        catch (Exception ex) { TxtPreview.Text = ex.Message; }
    }

    private void SyncIdeModeUi()
    {
        if (_loading || LblIdePath is null) return;
        LblIdePath.Text = RadioSketchbook.IsChecked == true ? "پوشه‌ی Sketchbook:" : "فایل boards.txt:";
    }

    // v0.9.54 - choosing a device now writes that device's real defaults into the step-1
    // advanced boxes AND the step-2 board form (both editable), so nothing has to be typed
    // by hand any more. An empty field always falls back to the selected identity's value.
    private void AnyField_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_loading) return;
        FillIdentityDefaults();
        FillBoardSpecFields();
        UpdatePreview();
    }

    private void FillIdentityDefaults()
    {
        if (TxtVid is null) return;
        var d = BoardHexService.DefaultsFor(CurrentIdentity.Key);
        _syncingSpecs = true;
        try
        {
            TxtVid.Text = d.BootVid;
            TxtPid.Text = d.BootPid;
            TxtProduct.Text = d.Product;
            TxtManuf.Text = d.Manufacturer;
        }
        finally { _syncingSpecs = false; }
    }

    /// <summary>v0.9.54 - fills step 2's board-spec form from the selected identity (plus the
    /// step-1 overrides when the advanced switch is on). The fields stay editable.</summary>
    private void FillBoardSpecFields()
    {
        if (TxtBoardId is null) return;
        var d = BoardHexService.DefaultsFor(CurrentIdentity.Key);
        var n = ResolveBoardNumbers();
        _syncingSpecs = true;
        try
        {
            TxtBoardId.Text = d.BoardId;
            TxtBoardName.Text = d.BoardName;
            TxtBootVid.Text = n.BootVid;
            TxtBootPid.Text = n.BootPid;
            TxtAppPid.Text = n.AppPid;
            TxtBoardProduct.Text = n.Product;
            TxtBoardManuf.Text = n.Manuf;
        }
        finally { _syncingSpecs = false; }
    }

    /// <summary>v0.9.54 - the single source the boards.txt block is built from: the step-2
    /// boxes win, and any box left empty falls back to the selected identity's default.</summary>
    private (string BoardId, string BoardName, string BootVid, string BootPid, string AppPid,
             string Product, string Manuf) BoardSpecsFromUi()
    {
        var n = ResolveBoardNumbers();
        var d = BoardHexService.DefaultsFor(CurrentIdentity.Key);
        static string Pick(System.Windows.Controls.TextBox? box, string fallback)
            => box is not null && box.Text.Trim().Length > 0 ? box.Text.Trim() : fallback;
        return (BoardHexService.SanitizeBoardId(Pick(TxtBoardId, d.BoardId)),
                Pick(TxtBoardName, d.BoardName),
                Pick(TxtBootVid, n.BootVid),
                Pick(TxtBootPid, n.BootPid),
                Pick(TxtAppPid, n.AppPid),
                Pick(TxtBoardProduct, n.Product),
                Pick(TxtBoardManuf, n.Manuf));
    }

    private void BoardSpec_Changed(object sender, System.Windows.Controls.TextChangedEventArgs e)
    {
        if (_loading || _syncingSpecs) return;
        UpdatePreview();
    }

    private void BtnSpecsReset_Click(object sender, RoutedEventArgs e)
    {
        FillBoardSpecFields();
        UpdatePreview();
        Log("مشخصات برد به پیش‌فرض دستگاه انتخاب‌شده بازگشت.");
    }

    private void BtnSpecsRefresh_Click(object sender, RoutedEventArgs e) => UpdatePreview();

    private void ChkCustom_Checked(object sender, RoutedEventArgs e)
    {
        if (_loading || GridAdvanced is null) return;
        GridAdvanced.Visibility = ChkCustom.IsChecked == true ? Visibility.Visible : Visibility.Collapsed;
        UpdatePreview();
    }

    private void IdeTarget_Changed(object sender, RoutedEventArgs e)
    {
        if (_loading) return;
        SyncIdeModeUi();
        UpdatePreview();
    }

    private void BtnIdeDetect_Click(object sender, RoutedEventArgs e)
    {
        if (RadioSketchbook.IsChecked == true)
        {
            TxtIdePath.Text = BoardsTxtService.DetectSketchbook();
            Log($"Sketchbook: {TxtIdePath.Text}");
            return;
        }
        var candidates = BoardsTxtService.DetectBoardsTxtCandidates();
        foreach (var (p, exists) in candidates)
            Log($"{(exists ? "✓" : "✗")} {p}");
        var found = candidates.FirstOrDefault(c => c.Exists);
        if (found.Path is not null) TxtIdePath.Text = found.Path;
        else if (candidates.Count > 0) TxtIdePath.Text = candidates[0].Path;
        else Log("هیچ boards.txt ای روی این سیستم پیدا نشد — مسیر را دستی انتخاب کن.");
    }

    private void BtnIdePathBrowse_Click(object sender, RoutedEventArgs e)
    {
        if (RadioSketchbook.IsChecked == true)
        {
            using var dlg = new System.Windows.Forms.FolderBrowserDialog { SelectedPath = TxtIdePath.Text };
            if (dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK) TxtIdePath.Text = dlg.SelectedPath;
        }
        else
        {
            var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "boards.txt|boards.txt|متن|*.txt" };
            if (dlg.ShowDialog(this) == true) TxtIdePath.Text = dlg.FileName;
        }
    }

    private async void BtnInstall_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var s = BoardSpecsFromUi();
            bool sketchbook = RadioSketchbook.IsChecked == true;
            var block = BoardsTxtService.BuildBoardBlock(boardId: s.BoardId, name: s.BoardName,
                bootVid: s.BootVid, bootPid: s.BootPid, appPid: s.AppPid, product: s.Product,
                manufacturer: s.Manuf, crossCore: sketchbook);
            var path = TxtIdePath.Text.Trim();
            if (path.Length == 0) throw new ArgumentException("مسیر نصب خالی است — «🔍 تشخیص خودکار» را بزن یا دستی انتخاب کن.");
            CollectSettings();
            SaveSettings();
            BtnInstall.IsEnabled = false;
            try
            {
                var msg = await Task.Run(() =>
                {
                    if (sketchbook)
                    {
                        var pkg = BoardsTxtService.InstallSketchbookPackage(path, block);
                        return $"✓ پکیج برد در Sketchbook نصب شد:\r\n{pkg}";
                    }
                    var backup = BoardsTxtService.InstallBoardBlock(path, block, s.BoardId);
                    return backup is null
                        ? $"✓ بلوک برد در فایل تازه نوشته شد:\r\n{path}"
                        : $"✓ بلوک برد به‌روز شد. بکاپ:\r\n{backup}";
                });
                Log(msg);
                SetStatus("نصب شد — Arduino IDE را یک بار ببند و باز کن");
            }
            finally { BtnInstall.IsEnabled = true; }
        }
        catch (Exception ex) { ShowError("خطا در نصب", ex); }
    }

    private async void BtnUninstall_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            bool sketchbook = RadioSketchbook.IsChecked == true;
            var path = TxtIdePath.Text.Trim();
            var boardId = BoardSpecsFromUi().BoardId;   // v0.9.54 - remove exactly what was installed
            BtnUninstall.IsEnabled = false;
            try
            {
                var removed = await Task.Run(() => sketchbook
                    ? BoardsTxtService.UninstallSketchbookPackage(path)
                    : BoardsTxtService.UninstallBoardBlock(path, boardId));
                Log(removed ? "✓ نصب برد حذف شد." : "چیزی برای حذف پیدا نشد (بلوک AMS حضور نداشت).");
                SetStatus(removed ? "حذف شد" : "چیزی برای حذف نبود");
            }
            finally { BtnUninstall.IsEnabled = true; }
        }
        catch (Exception ex) { ShowError("خطا در حذف", ex); }
    }

    // ───────────────────────────── tab 3: ISP flash ─────────────────────────────

    private void RefreshHexList()
    {
        if (_loading || CmbHex is null) return;
        var items = new List<string>();
        try
        {
            var dir = TxtOutputDir.Text.Trim();
            if (Directory.Exists(dir))
                items = Directory.GetFiles(dir, "Caterina-*.hex")
                    .OrderByDescending(File.GetLastWriteTime).ToList();
        }
        catch { /* an unreadable output folder just means an empty list */ }
        var current = CmbHex.Text;
        CmbHex.ItemsSource = items;
        CmbHex.Text = current.Length > 0 ? current : (items.Count > 0 ? items[0] : "");
    }

    private void RefreshFlashPorts()
    {
        if (_loading || CmbFlashPort is null) return;
        List<BoardCheckupService.PortInfo> ports;
        try { ports = BoardCheckupService.ScanPorts(); }
        catch { ports = new(); }
        CmbFlashPort.ItemsSource = ports.Select(p => p.Display).ToList();
        var pick = BoardCheckupService.PickProgrammerPort(ports);
        if (pick is not null && CmbFlashPort.Text.Trim().Length == 0)
            CmbFlashPort.Text = ports.First(p => p.Device == pick).Display;
    }

    /// <summary>Extracts "COMxx" from the combo text whether picked ("COMx — desc") or typed.</summary>
    private string SelectedPort()
        => CmbFlashPort.Text.Split(" — ")[0].Split(" - ")[0].Trim();

    private void BtnRefreshHex_Click(object sender, RoutedEventArgs e) { RefreshHexList(); UpdateManualCmd(); }

    private void BtnBrowseHex_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "HEX files|*.hex" };
        if (dlg.ShowDialog(this) == true) { CmbHex.Text = dlg.FileName; UpdateManualCmd(); }
    }

    private void BtnDetectPort_Click(object sender, RoutedEventArgs e)
    {
        CmbFlashPort.Text = "";
        RefreshFlashPorts();
        UpdateManualCmd();
    }

    private void FlashField_Changed(object sender, RoutedEventArgs e) => UpdateManualCmd();

    private void UpdateManualCmd()
    {
        if (_loading || TxtManualCmd is null) return;
        var script = BundledAssets.Find(AppContext.BaseDirectory, "tools", "isp_flash.py")
                     ?? Path.Combine(AppContext.BaseDirectory, "tools", "isp_flash.py");
        var toolsDir = Path.GetDirectoryName(script)!;
        var port = SelectedPort();
        if (port.Length == 0) port = "COM11";
        var hex = CmbHex.Text.Trim();
        var sb = new StringBuilder();
        sb.Append("cd \"").Append(toolsDir).Append("\"\r\n");
        sb.Append("python isp_flash.py --port ").Append(port).Append(" --check-only");
        if (ChkCheckOnly.IsChecked != true)
        {
            sb.Append("\r\npython isp_flash.py --port ").Append(port);
            if (hex.Length > 0) sb.Append(" --hex \"").Append(hex).Append("\"");
            if (ChkErase.IsChecked == true) sb.Append(" --erase");
            if (ChkFixFuses.IsChecked == true) sb.Append(" --fix-fuses");
        }
        TxtManualCmd.Text = sb.ToString();
    }

    private void BtnCopyCmd_Click(object sender, RoutedEventArgs e)
    {
        System.Windows.Clipboard.SetText(TxtManualCmd.Text);
        SetStatus("دستور فلش کپی شد — در PowerShell پیست و اجرا کن");
        Log("دستور فلش در کلیپ‌بورد کپی شد");
    }

    private async void BtnFlash_Click(object sender, RoutedEventArgs e)
    {
        if (_flashRunning) return;
        try
        {
            var script = BundledAssets.Find(AppContext.BaseDirectory, "tools", "isp_flash.py")
                ?? throw new FileNotFoundException("tools\\isp_flash.py کنار برنامه پیدا نشد.");
            var port = SelectedPort();
            if (port.Length == 0)
                throw new ArgumentException("پورت پروگرمر را انتخاب کن (یا «🔍 تشخیص پورت» را بزن).");
            bool checkOnly = ChkCheckOnly.IsChecked == true;
            var hex = CmbHex.Text.Trim();
            if (!checkOnly && !File.Exists(hex))
                throw new FileNotFoundException("فایل HEX معتبر انتخاب کن (تب «ساخت HEX» یا دکمه‌ی انتخاب).");

            var args = new List<string> { script, "--port", port };
            if (checkOnly) args.Add("--check-only");
            else
            {
                args.Add("--hex");
                args.Add(hex);
                if (ChkErase.IsChecked == true) args.Add("--erase");
                if (ChkFixFuses.IsChecked == true) args.Add("--fix-fuses");
            }

            CollectSettings();
            SaveSettings();
            _flashRunning = true;
            BtnFlash.IsEnabled = false;
            Log("⚡ اجرای isp_flash.py — خروجی زنده:");
            int code = await Task.Run(() => RunIspFlashStreaming(args));
            Log(code == 0 ? "✓ فلش کامل شد" : $"✗ isp_flash با کد {code} تمام شد — لاگ بالا را ببین");
            SetStatus(code == 0 ? "فلش موفق — برد را جدا و دوباره وصل کن" : "خطا در فلش — لاگ را ببین");
        }
        catch (Exception ex) { ShowError("خطا در فلش", ex); }
        finally { _flashRunning = false; BtnFlash.IsEnabled = true; }
    }

    /// <summary>Runs the bundled pure-Python ISP flasher with live output. Both streams are
    /// read asynchronously (the AmkImporter pipe-deadlock lesson) and python is resolved by
    /// the PATH, exactly like the serial bridge.</summary>
    private int RunIspFlashStreaming(List<string> args)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "python",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        foreach (var a in args) psi.ArgumentList.Add(a);
        using var proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        proc.OutputDataReceived += (_, ea) =>
        {
            if (ea.Data is { } d && d.Trim().Length > 0)
                Dispatcher.BeginInvoke(() => Log("  " + d));
        };
        proc.ErrorDataReceived += (_, ea) =>
        {
            if (ea.Data is { } d && d.Trim().Length > 0)
                Dispatcher.BeginInvoke(() => Log("  ! " + d));
        };
        proc.Start();
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();
        proc.WaitForExit();
        return proc.ExitCode;
    }

    // ───────────────────────────── tab 4: checkup ─────────────────────────────

    private async void BtnScan_Click(object sender, RoutedEventArgs e)
    {
        BtnScan.IsEnabled = false;
        try
        {
            _lastScan = await Task.Run(BoardCheckupService.ScanPorts);
            ListSummary.ItemsSource = null;
            RenderPortRows();
        }
        catch (Exception ex) { ShowError("خطا در اسکن", ex); }
        finally { BtnScan.IsEnabled = true; }
    }

    // v0.9.54 - the list shows attached ports only (the reference tool's behaviour); the
    // registry history rows are one checkbox away and still counted in the log line.
    private void RenderPortRows()
    {
        if (ListPorts is null) return;
        bool showHistory = ChkShowHistory?.IsChecked == true;
        ListPorts.ItemsSource = BoardCheckupService.VisibleRows(_lastScan, showHistory)
            .Select(BoardCheckupService.DescribePort).ToList();
        Log(BoardCheckupService.ScanSummaryLine(_lastScan, showHistory));
        var live = _lastScan.Count(r => !r.IsPhantom);
        SetStatus(showHistory
            ? $"{_lastScan.Count} ردیف ({live} وصل)"
            : $"{live} پورت وصل");
    }

    private void ChkShowHistory_Changed(object sender, RoutedEventArgs e)
    {
        if (_loading || _lastScan.Count == 0) return;
        RenderPortRows();
    }

    private async void BtnCheckup_Click(object sender, RoutedEventArgs e)
    {
        BtnCheckup.IsEnabled = false;
        Log("چکاپ کامل: اسکن + هندشیک HELLO (باز شدن پورت، برد 32U4 را ریست می‌کند — هر برد حدود ۲ ثانیه)…");
        try
        {
            var (rows, hs) = await Task.Run(() =>
            {
                var scanned = BoardCheckupService.ScanPorts();
                var answers = new Dictionary<string, string?>();
                foreach (var r in scanned.Where(r => r.Identity is not null && !r.IsProgrammer && !r.IsPhantom))
                    answers[r.Device] = BoardCheckupService.Handshake(r.Device);
                return (scanned, answers);
            });
            _lastScan = rows;
            RenderPortRows();
            var msgs = BoardCheckupService.SummarizeCheckup(rows, hs);
            ListSummary.ItemsSource = msgs.Select(m => $"{m.Icon}  {m.Text}").ToList();
            foreach (var m in msgs) Log($"{m.Icon} {m.Text}");
            SetStatus("چکاپ کامل شد");
        }
        catch (Exception ex) { ShowError("خطا در چکاپ", ex); }
        finally { BtnCheckup.IsEnabled = true; }
    }

    // v0.9.51 — dry-run list → explicit confirm → elevated one-shot cleanup with .reg backup
    private async void BtnCleanupCom_Click(object sender, RoutedEventArgs e)
    {
        BtnCleanupCom.IsEnabled = false;
        try
        {
            var rows = await Task.Run(BoardCheckupService.ScanPorts);
            // v0.9.53 — expand to bootloader+application PIDs so the dry-run list and the
            // elevated allow-list agree (v0.9.52 offered entries the elevated run then rejected)
            var allowed = BoardCleanupService.ExpandFamilies(BoardCheckupService.KnownVidPidSet());
            if (_s.UseCustomVp)
            {
                try
                {
                    var custom = (BoardHexService.ParseVidPid(_s.CustomVid, "VID"), BoardHexService.ParseVidPid(_s.CustomPid, "PID"));
                    foreach (var fam in BoardCleanupService.ExpandFamilies(new[] { custom })) allowed.Add(fam);
                }
                catch (Exception ex) { Log("i هویت سفارشی تب ۱ خوانده نشد و در پاکسازی لحاظ نمی‌شود: " + ex.Message); }
            }
            var candidates = BoardCheckupService.PhantomBoardsOfKnownFamilies(rows, allowed);
            if (candidates.Count == 0)
            {
                Log("🧹 تاریخچه‌ی قابل‌پاکسازی پیدا نشد — همه‌ی ورودی‌ها یا وصل‌اند یا متعلق به دستگاه‌های دیگرند");
                SetStatus("تاریخچه‌ای نیست");
                return;
            }
            var list = string.Join("\n", candidates.Select(c => $"  {c.Device}  ·  s/n {c.Serial}  ·  {c.Identity}"));
            var ask = System.Windows.MessageBox.Show(this,
                $"{candidates.Count} ورودی تاریخچه‌ی بردهای شناخته‌شده حذف می‌شود (فقط بردهایی که الان وصل نیستند):\n\n{list}\n\nپورت‌های آزادشده دوباره قابل‌استفاده می‌شوند. قبل از حذف بکاپ .reg گرفته می‌شود و اجرا یک‌بار اجازه‌ی ادمین (UAC) می‌خواهد.\nادامه می‌کنی؟",
                "پاکسازی تاریخچه‌ی COM", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question);
            if (ask != System.Windows.MessageBoxResult.Yes) { Log("پاکسازی تاریخچه لغو شد"); return; }
            var exeDir = AppContext.BaseDirectory;
            var req = new BoardCleanupService.CleanupRequest(
                candidates.Select(c => new BoardCleanupService.CleanupItem(c.RegPath, BoardCleanupService.PortNumber(c.Device)))
                          .Where(i => i.Port > 0).ToList(),
                allowed.Select(a => $"{a.Vid:X4}:{a.Pid:X4}").ToList(),
                exeDir, BoardCleanupService.ResultPath(exeDir));
            BoardCleanupService.WriteRequest(exeDir, req);
            Log($"🧹 پاکسازی با اجازه‌ی ادمین اجرا می‌شود… ({candidates.Count} ورودی)");
            var proc = BoardCleanupService.RelaunchElevated(exeDir);
            if (proc is null) { Log("اجرای ادمین شکست خورد"); return; }
            await Task.Run(() => proc.WaitForExit());
            foreach (var line in BoardCleanupService.ReadResult(exeDir)) Log("  " + line);
            var fresh = await Task.Run(BoardCheckupService.ScanPorts);
            _lastScan = fresh;
            RenderPortRows();
            SetStatus($"پاکسازی تمام شد — {fresh.Count} پورت باقی");
        }
        catch (System.ComponentModel.Win32Exception) { Log("پاکسازی لغو شد — اجازه‌ی ادمین داده نشد"); }
        catch (Exception ex) { ShowError("خطا در پاکسازی تاریخچه", ex); }
        finally { BtnCleanupCom.IsEnabled = true; }
    }
}
