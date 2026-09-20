using System.Diagnostics;
using System.IO.Ports;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using Ams.UI.Services;

namespace AMSBoardPrep;

public partial class MainWindow : Window
{
    private sealed record BoardProfile(
        string BoardId, string Serial, string Product, string Manufacturer,
        int Vid, int BootPid, int AppPid, string BootHex, string ProfileJson,
        string OutputDir);

    private readonly string _baseDir = AppContext.BaseDirectory;
    private BoardProfile? _profile;
    private bool _busy;

    public MainWindow()
    {
        InitializeComponent();
        CaterinaPath.Text = Path.Combine(_baseDir, "caterina", "Caterina.hex");
        OutputDir.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "AMSBoardPrep");
        Sketchbook.Text = BoardsTxtService.DetectSketchbook();
        RefreshProfilePaths();
        Log("نسخهٔ مستقل AMS Board Prep Debug آماده است.");
        Log("این برنامه عمداً فقط یک برد را در هر نوبت آماده می‌کند.");
    }

    private void Log(string text)
    {
        if (!Dispatcher.CheckAccess()) { Dispatcher.BeginInvoke(() => Log(text)); return; }
        LogBox.AppendText($"[{DateTime.Now:HH:mm:ss}] {text}{Environment.NewLine}");
        LogBox.ScrollToEnd();
    }

    private void SetStatus(string text, bool warning = false)
    {
        StatusText.Text = text;
        StatusText.Foreground = new System.Windows.Media.SolidColorBrush(
            (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(warning ? "#FBBF24" : "#86EFAC"));
    }

    private void RequireProfile()
    {
        if (_profile is null) throw new InvalidOperationException("ابتدا در تب ۱ برای همین برد یک HEX و Profile بساز.");
    }

    private void ChooseCaterina_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "Caterina HEX|*.hex|HEX|*.hex" };
        if (dlg.ShowDialog(this) == true) CaterinaPath.Text = dlg.FileName;
    }

    private void ChooseOutput_Click(object sender, RoutedEventArgs e)
    {
        using var dlg = new System.Windows.Forms.FolderBrowserDialog { SelectedPath = OutputDir.Text };
        if (dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK) OutputDir.Text = dlg.SelectedPath;
    }

    private static int ParseId(string text, string label)
        => BoardHexService.ParseVidPid(text, label);

    private BoardProfile ReadProfileInputs(string bootHex = "", string profileJson = "")
    {
        var boardId = BoardHexService.SanitizeBoardId(BoardId.Text.Trim());
        var serial = BoardHexService.ValidateSerial(Serial.Text);
        var product = BoardHexService.ValidateUsbString(Product.Text, "Product");
        var manufacturer = BoardHexService.ValidateUsbString(Manufacturer.Text, "Manufacturer");
        if (product.Length == 0) throw new ArgumentException("Product خالی است.");
        if (manufacturer.Length == 0) throw new ArgumentException("Manufacturer خالی است.");
        var vid = ParseId(Vid.Text, "VID");
        var bootPid = ParseId(BootPid.Text, "Boot PID");
        var appPid = ParseId(AppPid.Text, "App PID");
        if (appPid == bootPid) throw new ArgumentException("App PID باید با Boot PID متفاوت باشد.");
        return new(boardId, serial, product, manufacturer, vid, bootPid, appPid, bootHex, profileJson, OutputDir.Text.Trim());
    }

    private async void Generate_Click(object sender, RoutedEventArgs e)
    {
        if (_busy) return;
        try
        {
            var caterina = CaterinaPath.Text.Trim();
            var outDir = OutputDir.Text.Trim();
            if (!File.Exists(caterina)) throw new FileNotFoundException("Caterina.hex پیدا نشد.", caterina);
            if (outDir.Length == 0) throw new ArgumentException("پوشهٔ خروجی خالی است.");
            Directory.CreateDirectory(outDir);
            var draft = ReadProfileInputs();
            _busy = true;
            var profile = await Task.Run(() =>
            {
                var flash = BoardHexService.ParseHex(caterina);
                var patched = BoardHexService.PatchHex(flash, draft.Serial, draft.Vid, draft.BootPid,
                    classType: 0x02, subclass: 0x00, protocol: 0x00,
                    product: draft.Product, manufacturer: draft.Manufacturer);
                var hexName = $"Caterina-{draft.Serial}.hex";
                var hexPath = Path.Combine(outDir, hexName);
                File.WriteAllText(hexPath, BoardHexService.ToHex(patched), Encoding.ASCII);
                var jsonName = $"Board-{draft.Serial}.json";
                var jsonPath = Path.Combine(outDir, jsonName);
                var json = new
                {
                    schema = "ams-board-profile-v2",
                    mode = "single-manual",
                    boardId = draft.BoardId,
                    serial = draft.Serial,
                    product = draft.Product,
                    manufacturer = draft.Manufacturer,
                    vid = $"0x{draft.Vid:X4}",
                    bootPid = $"0x{draft.BootPid:X4}",
                    appPid = $"0x{draft.AppPid:X4}",
                    bootloaderHex = hexName,
                    applicationMustBeBuiltAfterIdeInstall = true,
                    applicationIdentityMustMatch = true
                };
                File.WriteAllText(jsonPath, JsonSerializer.Serialize(json, new JsonSerializerOptions { WriteIndented = true }), Encoding.UTF8);
                return draft with { BootHex = hexPath, ProfileJson = jsonPath };
            });
            _profile = profile;
            BootHex.Text = profile.BootHex;
            ProfileSummary.Text = ProfileText(profile);
            SetStatus("Profile فعال شد — مرحلهٔ بعد: نصب در IDE");
            Log($"✓ یک HEX ساخته شد: {profile.BootHex}");
            Log($"✓ یک Profile ساخته شد: {profile.ProfileJson}");
        }
        catch (Exception ex) { ShowError("ساخت HEX", ex); }
        finally { _busy = false; }
    }

    private static string ProfileText(BoardProfile p)
        => $"Profile فعال: {p.Product} · Serial={p.Serial} · VID=0x{p.Vid:X4} · Boot PID=0x{p.BootPid:X4} · App PID=0x{p.AppPid:X4}";

    private void ClearProfile_Click(object sender, RoutedEventArgs e)
    {
        _profile = null;
        BootHex.Text = "";
        ProfileSummary.Text = "";
        SetStatus("پروفایل فعال وجود ندارد", true);
        Log("پروفایل فعال پاک شد؛ برای برد بعدی از تب ۱ شروع کن.");
    }

    private void DetectSketchbook_Click(object sender, RoutedEventArgs e)
    {
        Sketchbook.Text = BoardsTxtService.DetectSketchbook();
        Log("Sketchbook: " + Sketchbook.Text);
    }

    private async void InstallIde_Click(object sender, RoutedEventArgs e)
    {
        if (_busy) return;
        try
        {
            RequireProfile();
            var path = Sketchbook.Text.Trim();
            if (path.Length == 0) throw new ArgumentException("مسیر Sketchbook خالی است.");
            var p = _profile!;
            var block = BoardsTxtService.BuildBoardBlock(
                boardId: p.BoardId, name: "Classroom Studio Board",
                bootVid: $"0x{p.Vid:X4}", bootPid: $"0x{p.BootPid:X4}", appPid: $"0x{p.AppPid:X4}",
                product: p.Product, manufacturer: p.Manufacturer, serial: p.Serial, crossCore: false);
            _busy = true;
            await Task.Run(() => BoardsTxtService.InstallSketchbookPackage(path, block, p.Serial));
            SetStatus("Profile در IDE نصب شد — Arduino IDE را ببند و باز کن");
            Log("✓ پکیج خصوصی IDE نصب شد؛ Serial این پکیج: " + p.Serial);
        }
        catch (Exception ex) { ShowError("نصب در IDE", ex); }
        finally { _busy = false; }
    }

    private async void UninstallIde_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var removed = await Task.Run(() => BoardsTxtService.UninstallSketchbookPackage(Sketchbook.Text.Trim()));
            Log(removed ? "✓ پکیج مستقل IDE حذف شد." : "پکیج مستقلی برای حذف پیدا نشد.");
        }
        catch (Exception ex) { ShowError("حذف پکیج IDE", ex); }
    }

    private void RefreshProfilePaths_Click(object sender, RoutedEventArgs e) => RefreshProfilePaths();

    private void RefreshProfilePaths()
    {
        if (_profile is not null)
        {
            BootHex.Text = _profile.BootHex;
            ProfileSummary.Text = ProfileText(_profile);
        }
    }

    private void ScanPorts_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var rows = BoardCheckupService.ScanPorts();
            PortsList.Items.Clear();
            foreach (var row in rows.Where(r => !r.IsPhantom)) PortsList.Items.Add(BoardCheckupService.DescribePort(row));
            var programmer = BoardCheckupService.PickProgrammerPort(rows.Where(r => !r.IsPhantom).ToList());
            if (programmer is not null && string.IsNullOrWhiteSpace(ProgrammerPort.Text)) ProgrammerPort.Text = programmer;
            Log(BoardCheckupService.ScanSummaryLine(rows, false));
        }
        catch (Exception ex) { ShowError("اسکن پورت", ex); }
    }

    private async void FlashIsp_Click(object sender, RoutedEventArgs e)
    {
        if (_busy) return;
        try
        {
            RequireProfile();
            var port = ProgrammerPort.Text.Trim();
            if (!port.StartsWith("COM", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("پورت ArduinoISP را مثل COM33 وارد کن.");
            if (!File.Exists(_profile!.BootHex)) throw new FileNotFoundException("HEX بوت‌لودر Profile پیدا نشد.", _profile.BootHex);
            var script = Path.Combine(_baseDir, "tools", "isp_flash.py");
            if (!File.Exists(script)) throw new FileNotFoundException("isp_flash.py کنار برنامه پیدا نشد.", script);
            var args = new List<string> { script, "--port", port };
            if (CheckOnly.IsChecked == true) args.Add("--check-only");
            else
            {
                args.Add("--hex"); args.Add(_profile.BootHex);
                if (Erase.IsChecked == true) args.Add("--erase");
                if (FixFuses.IsChecked == true) args.Add("--fix-fuses");
            }
            _busy = true;
            Log("── اجرای ISP برای Profile فعال ──");
            var code = await Task.Run(() => RunProcess("python", args));
            if (code == 0) { SetStatus("ISP موفق — کابل ISP را جدا کن و وارد مرحلهٔ Application شو"); Log("✓ ISP با کد صفر تمام شد."); }
            else { SetStatus("ISP ناموفق", true); Log("✗ ISP با کد " + code + " تمام شد."); }
        }
        catch (Exception ex) { ShowError("فلش ISP", ex); }
        finally { _busy = false; }
    }

    private void ChooseAppIsp_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "Application HEX|*.hex|HEX|*.hex" };
        if (dlg.ShowDialog(this) == true) { AppIspHex.Text = dlg.FileName; ValidateAppIsp(); }
    }

    private void ValidateAppIsp_Click(object sender, RoutedEventArgs e) => ValidateAppIsp();

    private bool ValidateAppIsp()
    {
        try
        {
            RequireProfile();
            var info = HexInspector.RequireApplicationOnly(AppIspHex.Text.Trim());
            AppIspValidation.Text = $"✓ App-only معتبر: {info.Range} · {info.DataBytes:N0} bytes · Bootloader حفظ می‌شود\nProfile مورد انتظار: {_profile!.Product} / {_profile.Serial}";
            AppIspValidation.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Colors.LightGreen);
            return true;
        }
        catch (Exception ex)
        {
            AppIspValidation.Text = "✗ " + ex.Message;
            AppIspValidation.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Colors.Orange);
            return false;
        }
    }

    private async void FlashApplicationIsp_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || !ValidateAppIsp()) return;
        try
        {
            RequireProfile();
            var port = AppIspPort.Text.Trim();
            if (!port.StartsWith("COM", StringComparison.OrdinalIgnoreCase)) throw new ArgumentException("پورت ArduinoISP را مثل COM33 وارد کن.");
            var script = Path.Combine(_baseDir, "tools", "isp_flash_app_only.py");
            if (!File.Exists(script)) throw new FileNotFoundException("isp_flash_app_only.py کنار برنامه پیدا نشد.", script);
            _busy = true;
            Log("── فلش اضطراری Application با ISP؛ Bootloader حفظ می‌شود ──");
            var code = await Task.Run(() => RunProcess("python", new List<string> { script, "--app-only", "--port", port, "--hex", AppIspHex.Text.Trim() }));
            if (code == 0) { SetStatus("Application با ISP نصب شد — چکاپ را اجرا کن"); Log("✓ Application ISP موفق شد؛ Bootloader دست‌نخورده ماند."); }
            else { SetStatus("فلش Application با ISP ناموفق", true); Log("✗ Application ISP با کد " + code + " تمام شد."); }
        }
        catch (Exception ex) { ShowError("فلش Application با ISP", ex); }
        finally { _busy = false; }
    }

    private void ChooseApplication_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "Application HEX|*.hex|HEX|*.hex" };
        if (dlg.ShowDialog(this) == true) { ApplicationHex.Text = dlg.FileName; ValidateApplication(); }
    }

    private void ValidateApplication_Click(object sender, RoutedEventArgs e) => ValidateApplication();

    private bool ValidateApplication()
    {
        try
        {
            RequireProfile();
            var info = HexInspector.RequireApplicationOnly(ApplicationHex.Text.Trim());
            ApplicationValidation.Text = $"✓ App-only معتبر: {info.Range} · {info.DataBytes:N0} bytes · SHA-256 {info.Sha256}\nProfile مورد انتظار: {_profile!.Product} / {_profile.Serial} / App PID 0x{_profile.AppPid:X4}";
            ApplicationValidation.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Colors.LightGreen);
            Log("✓ Application HEX فقط از نظر محدوده معتبر است؛ باید بعد از نصب Profile در IDE ساخته شده باشد.");
            return true;
        }
        catch (Exception ex)
        {
            ApplicationValidation.Text = "✗ " + ex.Message;
            ApplicationValidation.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Colors.Orange);
            return false;
        }
    }

    private void DetectRuntime_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            RequireProfile();
            var row = FindPort(_profile!.Vid, _profile.AppPid, _profile.Serial, allowSingleFallback: true);
            RuntimePort.Text = row?.Device ?? "AUTO";
            Log(row is null ? "Runtime برای Profile فعال پیدا نشد." : $"Runtime انتخاب شد: {row.Device} · Serial={row.Serial}");
        }
        catch (Exception ex) { ShowError("تشخیص Runtime", ex); }
    }

    private async void UploadApplication_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || !ValidateApplication()) return;
        try
        {
            RequireProfile();
            var appHex = ApplicationHex.Text.Trim();
            var p = _profile!;
            var avrdude = FindAvrDude();
            if (avrdude is null) throw new FileNotFoundException("avrdude.exe در Arduino15 پیدا نشد؛ ابتدا Arduino AVR Boards را نصب کن.");
            _busy = true;
            Log("── آپدیت Application با USB؛ بدون ISP و بدون Chip Erase ──");
            var result = await Task.Run(() => UploadUsb(p, appHex, RuntimePort.Text.Trim(), avrdude.Value));
            SetStatus("Application موفق — چکاپ نهایی را اجرا کن");
            Log("✓ Application روی " + result + " نصب شد.");
        }
        catch (Exception ex) { SetStatus("آپدیت Application ناموفق؛ بوت‌لودر حفظ شده است", true); ShowError("آپدیت Application", ex); }
        finally { _busy = false; }
    }

    private (string Exe, string Config)? FindAvrDude()
    {
        var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Arduino15", "packages", "arduino", "tools", "avrdude");
        if (!Directory.Exists(root)) return null;
        foreach (var dir in Directory.GetDirectories(root).OrderByDescending(x => x, StringComparer.OrdinalIgnoreCase))
        {
            var exe = Path.Combine(dir, "bin", "avrdude.exe");
            var cfg = Path.Combine(dir, "etc", "avrdude.conf");
            if (File.Exists(exe) && File.Exists(cfg)) return (exe, cfg);
        }
        return null;
    }

    private string UploadUsb(BoardProfile p, string appHex, string runtimeText, (string Exe, string Config) avrdude)
    {
        var runtime = runtimeText.Equals("AUTO", StringComparison.OrdinalIgnoreCase) || runtimeText.Length == 0
            ? FindPort(p.Vid, p.AppPid, p.Serial, true)?.Device
            : ExtractCom(runtimeText);
        if (string.IsNullOrWhiteSpace(runtime)) throw new InvalidOperationException("Runtime برد فعال پیدا نشد.");
        Log($"Runtime فعلی: {runtime} · Profile Serial={p.Serial}");
        Touch1200(runtime);
        Log("1200-bps touch ارسال شد؛ منتظر Bootloader و آماده‌شدن واقعی پورت هستیم…");
        var boot = WaitForPort(p.Vid, p.BootPid, p.Serial, 20);
        if (boot is null) throw new TimeoutException("Bootloader مورد انتظار ظاهر نشد.");
        Log($"Bootloader پیدا شد: {boot.Device}; تست بازشدن پورت…");
        var args = new List<string> { "-C", avrdude.Config, "-v", "-p", "atmega32u4", "-c", "avr109", "-P", boot.Device, "-b", "57600", "-D", "-U", $"flash:w:{appHex}:i" };
        var code = RunProcess(avrdude.Exe, args);
        if (code != 0) throw new InvalidOperationException($"avrdude با کد {code} برگشت.");
        Log("avrdude موفق شد؛ منتظر برگشت Application همان Serial هستیم…");
        var app = WaitForPort(p.Vid, p.AppPid, p.Serial, 20);
        if (app is null) throw new TimeoutException("Application با همان Serial بعد از آپلود دیده نشد.");
        try { var hello = BoardCheckupService.Handshake(app.Device); if (!string.IsNullOrWhiteSpace(hello)) Log("HELLO: " + hello); } catch { }
        return app.Device;
    }

    private static string ExtractCom(string value)
        => value.Split(" — ", StringSplitOptions.None)[0].Split(" - ", StringSplitOptions.None)[0].Trim();

    private static void Touch1200(string port)
    {
        using var serial = new SerialPort(port, 1200) { DtrEnable = true, RtsEnable = true, ReadTimeout = 250, WriteTimeout = 250 };
        serial.Open(); Thread.Sleep(120); serial.Close();
    }

    private BoardCheckupService.PortInfo? WaitForPort(int vid, int pid, string serial, int seconds)
    {
        var until = DateTime.UtcNow.AddSeconds(seconds);
        while (DateTime.UtcNow < until)
        {
            var hit = FindPort(vid, pid, serial, allowSingleFallback: true);
            if (hit is not null && TryOpenPort(hit.Device)) return hit;
            Thread.Sleep(250);
        }
        return null;
    }

    private static bool TryOpenPort(string port)
    {
        try
        {
            using var serial = new SerialPort(port, 57600) { DtrEnable = false, RtsEnable = false, ReadTimeout = 150, WriteTimeout = 150 };
            serial.Open(); serial.Close(); return true;
        }
        catch { return false; }
    }

    private BoardCheckupService.PortInfo? FindPort(int vid, int pid, string serial, bool allowSingleFallback)
    {
        var candidates = BoardCheckupService.ScanPorts().Where(r => !r.IsPhantom && !r.IsProgrammer && r.Vid == vid && r.Pid == pid).ToList();
        var exact = candidates.FirstOrDefault(r => string.Equals(r.Serial, serial, StringComparison.OrdinalIgnoreCase));
        if (exact is not null) return exact;
        if (allowSingleFallback && candidates.Count == 1) return candidates[0];
        if (candidates.Count > 1) Log($"چند پورت با {vid:X4}:{pid:X4} پیدا شد؛ چون Serial تطبیق ندارد انتخاب متوقف شد.");
        return null;
    }

    private async void Checkup_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            RequireProfile();
            ScanPorts_Click(sender, e);
            var p = _profile!;
            var rows = BoardCheckupService.ScanPorts().Where(r => !r.IsPhantom && r.Vid == p.Vid && (r.Pid == p.BootPid || r.Pid == p.AppPid)).ToList();
            var exact = rows.FirstOrDefault(r => string.Equals(r.Serial, p.Serial, StringComparison.OrdinalIgnoreCase));
            if (exact is null) { SetStatus("چکاپ ناموفق — همان Serial پیدا نشد", true); Log("✗ Profile فعال پیدا نشد: " + p.Serial); return; }
            Log($"✓ Profile دقیق پیدا شد: {exact.Device} · {exact.Vid:X4}:{exact.Pid:X4} · {exact.Serial}");
            if (exact.Pid == p.AppPid) { var hello = await Task.Run(() => BoardCheckupService.Handshake(exact.Device)); Log(string.IsNullOrWhiteSpace(hello) ? "⚠ Application دیده شد ولی HELLO نیامد." : "✓ HELLO: " + hello); }
            SetStatus("چکاپ موفق — هویت و PID/Serial با Profile برابر است");
        }
        catch (Exception ex) { ShowError("چکاپ", ex); }
    }

    private async Task<int> RunProcessAsync(string file, IReadOnlyList<string> args) => await Task.Run(() => RunProcess(file, args));

    private int RunProcess(string file, IReadOnlyList<string> args)
    {
        var psi = new ProcessStartInfo { FileName = file, UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8 };
        foreach (var arg in args) psi.ArgumentList.Add(arg);
        Log("> " + file + " " + string.Join(" ", args.Select(Quote)));
        using var process = new Process { StartInfo = psi };
        process.Start();
        var stdout = process.StandardOutput.ReadToEndAsync();
        var stderr = process.StandardError.ReadToEndAsync();
        process.WaitForExit();
        foreach (var line in stdout.GetAwaiter().GetResult().SplitLines()) Log(line);
        foreach (var line in stderr.GetAwaiter().GetResult().SplitLines()) Log("! " + line);
        return process.ExitCode;
    }

    private static string Quote(string s) => s.Any(char.IsWhiteSpace) ? "\"" + s + "\"" : s;

    private static IEnumerable<string> SplitLines(string text)
        => text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

    private void Tabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (e.Source == Tabs && Tabs.SelectedIndex > 0 && _profile is null)
            SetStatus("ابتدا در تب ۱ یک Profile بساز", true);
    }

    private void ShowError(string title, Exception ex)
    {
        Log("✗ " + title + ": " + ex.Message);
        MessageBox.Show(this, ex.Message, title, MessageBoxButton.OK, MessageBoxImage.Warning);
    }
}
