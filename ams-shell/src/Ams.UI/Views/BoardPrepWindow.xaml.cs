// v0.9.50 — Board preparation window (the AMS USB Studio tool ported into Classroom
// Studio). Fleet v0.9.60: count>1 creates deterministic Product/Serial profiles and a manifest.
// Four tabs: build a Caterina HEX with a custom USB identity, install the board
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
        public bool CheckOnly { get; set; } = true;
        public bool Erase { get; set; } = false;
        public bool FixFuses { get; set; }
    }

    private readonly Settings _s;
    private readonly string _settingsPath;
    private bool _loading = true;
    private bool _flashRunning;
    private int _step = 1;
    private bool _syncingSpecs;
    private List<BoardCheckupService.PortInfo> _lastScan = new();

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
        TxtOutputDir.Text = _s.OutputDir.Length > 0 ? _s.OutputDir : Path.Combine(AppContext.BaseDirectory, "patches");
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

    private void Log(string msg) { TxtLog.AppendText(msg + Environment.NewLine); TxtLog.ScrollToEnd(); }
    private void SetStatus(string msg) => TxtStatus.Text = msg;
    private void ShowPanel(FrameworkElement panel, System.Windows.Controls.Primitives.ToggleButton tab) { if (_loading) return; PanelHex.Visibility=Visibility.Collapsed; PanelIde.Visibility=Visibility.Collapsed; PanelFlash.Visibility=Visibility.Collapsed; PanelCheckup.Visibility=Visibility.Collapsed; panel.Visibility=Visibility.Visible; TabHex.IsChecked=tab==TabHex; TabIde.IsChecked=tab==TabIde; TabFlash.IsChecked=tab==TabFlash; TabCheckup.IsChecked=tab==TabCheckup; _step=tab==TabHex?1:tab==TabIde?2:tab==TabFlash?3:4; SyncWizardNav(); }
    internal static string StepHint(int step) => step switch { 1=>"قدم ۱ از ۴ · ساخت HEX — هویت دستگاه، سریال و مشخصات برد فقط همین‌جا وارد می‌شود",2=>"قدم ۲ از ۴ · نصب در IDE — همان مشخصات قدم ۱ خودکار اینجاست؛ فقط محل نصب را تأیید کن",3=>"قدم ۳ از ۴ · فلش ISP — برد پروگرمر با شش سیم به برد مقصد، و خودش با USB به کامپیوتر",_=>"قدم ۴ از ۴ · چکاپ برد — فقط می‌خواند و چیزی روی برد نمی‌نویسد" };
    internal static int ClampStep(int step)=>step<1?1:step>4?4:step;
    private void SyncWizardNav(){if(TxtStepHint is null)return;TxtStepHint.Text=StepHint(_step);BtnPrevStep.IsEnabled=_step>1;BtnNextStep.IsEnabled=_step<4;}
    private void GoStep(int step){switch(ClampStep(step)){case 1:ShowPanel(PanelHex,TabHex);break;case 2:ShowPanel(PanelIde,TabIde);break;case 3:ShowPanel(PanelFlash,TabFlash);break;default:ShowPanel(PanelCheckup,TabCheckup);break;}}
    private void BtnNextStep_Click(object s,RoutedEventArgs e)=>GoStep(_step+1); private void BtnPrevStep_Click(object s,RoutedEventArgs e)=>GoStep(_step-1); private void TabHex_Click(object s,RoutedEventArgs e)=>ShowPanel(PanelHex,TabHex); private void TabIde_Click(object s,RoutedEventArgs e)=>ShowPanel(PanelIde,TabIde); private void TabFlash_Click(object s,RoutedEventArgs e)=>ShowPanel(PanelFlash,TabFlash); private void TabCheckup_Click(object s,RoutedEventArgs e)=>ShowPanel(PanelCheckup,TabCheckup);
    private BoardHexService.DeviceMode CurrentIdentity=>CmbIdentity.SelectedItem as BoardHexService.DeviceMode??BoardHexService.DeviceModes[0];
    private Settings LoadSettings(){try{if(File.Exists(_settingsPath))return JsonSerializer.Deserialize<Settings>(File.ReadAllText(_settingsPath))??new Settings();}catch{}return new Settings();}
    private void CollectSettings(){_s.IdentityKey=CurrentIdentity.Key;_s.Serial=TxtSerial.Text;_s.Prefix=TxtPrefix.Text;_s.Count=TxtCount.Text;_s.UseCustomVp=ChkCustom.IsChecked==true;_s.CustomVid=TxtVid.Text;_s.CustomPid=TxtPid.Text;_s.CustomProduct=TxtProduct.Text;_s.CustomManuf=TxtManuf.Text;_s.CaterinaPath=TxtCaterina.Text;_s.OutputDir=TxtOutputDir.Text;_s.TargetSketchbook=RadioSketchbook.IsChecked==true;_s.IdePath=TxtIdePath.Text;_s.FlashHex=CmbHex.Text;_s.FlashPort=CmbFlashPort.Text;_s.CheckOnly=ChkCheckOnly.IsChecked==true;_s.Erase=ChkErase.IsChecked==true;_s.FixFuses=ChkFixFuses.IsChecked==true;}
    private void SaveSettings(){try{File.WriteAllText(_settingsPath,JsonSerializer.Serialize(_s,new JsonSerializerOptions{WriteIndented=true}));}catch{}}
    protected override void OnClosed(EventArgs e){CollectSettings();SaveSettings();base.OnClosed(e);}
    private void ShowError(string title,Exception ex)=>System.Windows.MessageBox.Show(this,ex.Message,title,MessageBoxButton.OK,MessageBoxImage.Warning);
    private (int? Vid,int? Pid,int Cls,int Sub,int Proto,string? Product,string? Manuf) ResolveIdentityConfig(){var preset=CurrentIdentity;int? vid=null,pid=null;string? product=null,manuf=null;if(preset.Key!="none"){vid=preset.Vid;pid=preset.Pid;product=preset.Product;manuf=preset.Manufacturer;}if(ChkCustom.IsChecked==true){vid=BoardHexService.ParseVidPid(TxtVid.Text,"VID");pid=BoardHexService.ParseVidPid(TxtPid.Text,"PID");}var cp=BoardHexService.ValidateUsbString(TxtProduct.Text,"نام محصول");var cm=BoardHexService.ValidateUsbString(TxtManuf.Text,"سازنده");if(cp.Length>0)product=cp;if(cm.Length>0)manuf=cm;return(vid,pid,preset.ClassType,preset.Subclass,preset.Protocol,product,manuf);}
    private void BtnRandom_Click(object s,RoutedEventArgs e){var prefix=TxtPrefix.Text.Trim();TxtSerial.Text=BoardHexService.GenerateRandomSerial(prefix.Length>0?prefix:"AMS");}
    private void BtnBrowseCaterina_Click(object s,RoutedEventArgs e){var dlg=new Microsoft.Win32.OpenFileDialog{Filter="Caterina HEX|Caterina*.hex|HEX files|*.hex"};if(dlg.ShowDialog(this)==true)TxtCaterina.Text=dlg.FileName;}
    private void BtnBrowseOutput_Click(object s,RoutedEventArgs e){using var dlg=new System.Windows.Forms.FolderBrowserDialog{SelectedPath=TxtOutputDir.Text};if(dlg.ShowDialog()==System.Windows.Forms.DialogResult.OK)TxtOutputDir.Text=dlg.SelectedPath;}
    private static string FleetProduct(string template,int number,int count){var value=(template??"").Trim();if(value.Length==0)value="AMS Macro Studio";var token=number.ToString("D2");bool templated=value.Contains("{n}",StringComparison.OrdinalIgnoreCase)||value.Contains("{id}",StringComparison.OrdinalIgnoreCase);value=value.Replace("{n}",token,StringComparison.OrdinalIgnoreCase).Replace("{id}",token,StringComparison.OrdinalIgnoreCase);if(count>1&&!templated)value+=" "+token;return BoardHexService.ValidateUsbString(value,"نام محصول");}
    private static string FleetSerial(string prefix,int number,int count,string single){if(count==1)return BoardHexService.ValidateSerial(single);var p=(prefix??"").Trim();if(p.Length==0)p="AMS";return BoardHexService.ValidateSerial($"{p}-{number:D4}");}
    private async void BtnGenerate_Click(object sender,RoutedEventArgs e){try{if(!int.TryParse(TxtCount.Text,out int count)||count<1||count>500)throw new ArgumentException("تعداد باید یک عدد بین ۱ تا ۵۰۰ باشد");var cfg=ResolveIdentityConfig();var productTemplate=TxtProduct.Text.Trim().Length>0?TxtProduct.Text.Trim():(cfg.Product??CurrentIdentity.Product);var fleet=Enumerable.Range(1,count).Select(number=>(Number:number,Serial:FleetSerial(TxtPrefix.Text,number,count,TxtSerial.Text),Product:FleetProduct(productTemplate,number,count))).ToList();if(fleet.Select(x=>x.Serial).Distinct(StringComparer.OrdinalIgnoreCase).Count()!=fleet.Count)throw new ArgumentException("Serialهای تولیدشده تکراری هستند؛ پیشوند یا تعداد را تغییر بده.");if(fleet.Select(x=>x.Product).Distinct(StringComparer.OrdinalIgnoreCase).Count()!=fleet.Count)throw new ArgumentException("نام‌های محصول تولیدشده تکراری هستند؛ در نام محصول از {n} یا {id} استفاده کن.");var caterina=TxtCaterina.Text.Trim();if(!File.Exists(caterina))throw new FileNotFoundException("Caterina.hex پیدا نشد — از کارت «مسیرها» مسیر درست را انتخاب کن.");var outDir=TxtOutputDir.Text.Trim();if(outDir.Length==0)throw new ArgumentException("پوشه‌ی خروجی خالی است.");CollectSettings();SaveSettings();BtnGenerate.IsEnabled=false;try{var result=await Task.Run(()=>{Directory.CreateDirectory(outDir);var flash=BoardHexService.ParseHex(caterina);var lines=new List<string>();int curVid=flash[BoardHexService.DeviceDescOffset+8]|(flash[BoardHexService.DeviceDescOffset+9]<<8);int curPid=flash[BoardHexService.DeviceDescOffset+10]|(flash[BoardHexService.DeviceDescOffset+11]<<8);lines.Add($"خواندن {Path.GetFileName(caterina)} …");lines.Add($"هویت فعلی فایل: VID 0x{curVid:X4} PID 0x{curPid:X4}");lines.Add(cfg.Vid is not null?$"هویت جدید: VID 0x{cfg.Vid:X4} PID 0x{cfg.Pid:X4} class 0x{cfg.Cls:X2}":"هویت دستگاه بدون تغییر می‌ماند (فقط سریال پچ می‌شود)");int okCount=0,errCount=0;var manifest=new List<object>();foreach(var board in fleet){try{var patched=BoardHexService.PatchHex(flash,board.Serial,cfg.Vid,cfg.Pid,cfg.Cls,cfg.Sub,cfg.Proto,board.Product,cfg.Manuf);var fileName=$"Caterina-{board.Serial}.hex";File.WriteAllText(Path.Combine(outDir,fileName),BoardHexService.ToHex(patched),Encoding.ASCII);var profileName=$"Board-{board.Number:D2}-{board.Serial}.json";var profile=new{schema="ams-board-profile-v1",boardNumber=board.Number,serial=board.Serial,product=board.Product,manufacturer=cfg.Manuf,bootVid=cfg.Vid,bootPid=cfg.Pid,applicationPid=cfg.Pid is null?null:cfg.Pid+1,bootloaderHex=fileName,applicationBuildRequired=true,applicationBuildNote="Arduino IDE را با همین Serial و Product کامپایل کن"};File.WriteAllText(Path.Combine(outDir,profileName),JsonSerializer.Serialize(profile,new JsonSerializerOptions{WriteIndented=true}),Encoding.UTF8);manifest.Add(profile);lines.Add($" ✓ {fileName} · {board.Product} · {board.Serial}");okCount++;}catch(Exception ex){lines.Add($" ✗ {board.Serial}: {ex.Message}");errCount++;}}File.WriteAllText(Path.Combine(outDir,"fleet-manifest.json"),JsonSerializer.Serialize(new{schema="ams-board-fleet-v1",count=manifest.Count,boards=manifest},new JsonSerializerOptions{WriteIndented=true}),Encoding.UTF8);File.WriteAllText(Path.Combine(outDir,"README-fleet-fa.txt"),"برای هر برد: ابتدا HEX بوت‌لودر متناظر با همان Serial را با ISP نصب کن؛ سپس Application را با همان Product و Serial در Arduino IDE کامپایل و Upload کن.\r\nهرگز HEX بوت‌لودر یک برد را روی برد دیگر استفاده نکن.\r\n",Encoding.UTF8);return(lines,okCount,errCount);});foreach(var l in result.lines)Log(l);Log($"نتیجه: {result.okCount} فایل ساخته شد"+(result.errCount>0?$"، {result.errCount} خطا":""));Log($"پوشه: {outDir}");SetStatus($"تکمیل شد — {result.okCount} فایل ساخته شد؛ قدم بعد: تب «فلش ISP»");RefreshHexList();}finally{BtnGenerate.IsEnabled=true;}}catch(Exception ex){ShowError("خطا در ورودی",ex);}}
}
