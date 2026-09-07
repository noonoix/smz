# جلسهٔ ۲۰۲۶-08-20 — باگ‌های v0.5

## خلاصه
بیلد v0.5 با خطاهای `MSB3021/MSB3027` (قفل فایل exe) و `CS0104` (ambiguity بین System.Drawing و System.Windows) شکست می‌خورد. تمام خطاها رفع شدند و برنامه اجرا شد. یک باگ تولید اسکریپت PowerShell هم فیکس شد.

---

## خطاهای بیلد رفع‌شده

### CS0104: Application ambiguous
- **علت:** `<UseWindowsForms>true</UseWindowsForms>` در csproj باعث import شدن `System.Windows.Forms` شد که خودش `Application` دارد.
- **رفع:** عوض کردن `Application.Current` به `System.Windows.Application.Current` در ۳ فایل:
  - [App.xaml.cs](src/Ams.UI/App.xaml.cs)
  - [StepDialog.xaml.cs](src/Ams.UI/Views/StepDialog.xaml.cs)
  - [MainViewModel.cs](src/Ams.UI/ViewModels/MainViewModel.cs)

### CS0104: OpenFileDialog / SaveFileDialog ambiguous
- **رفع:** استفاده از `Microsoft.Win32.OpenFileDialog` و `Microsoft.Win32.SaveFileDialog` در `MainViewModel.cs`.

### CS0104: MessageBox ambiguous
- **رفع:** استفاده از `System.Windows.MessageBox.Show` در `MainViewModel.cs`.

### CS0104: Point / MouseEventArgs / KeyEventArgs ambiguous
- **رفع:** استفاده از `System.Windows.Point` و `System.Windows.Input.MouseEventArgs` و `System.Windows.Input.KeyEventArgs` در [RegionPickerWindow.xaml.cs](src/Ams.UI/Views/RegionPickerWindow.xaml.cs).

### CS0104: Brush / Brushes ambiguous
- **رفع:** استفاده از `System.Windows.Media.Brush` و `System.Windows.Media.Brushes` در converterها و StepDialog.

### CS0104: FontFamily ambiguous
- **رفع:** `System.Windows.Media.FontFamily` در [StepDialog.xaml.cs](src/Ams.UI/Views/StepDialog.xaml.cs).

### CS0176: HorizontalAlignment.Left instance access
- **رفع:** `System.Windows.HorizontalAlignment.Left`.

### CS0234: ComboBox/CheckBox not in WPF-UI
- **علت:** WPF-UI 3.0.5 رشته‌های «ComboBox» و «CheckBox» را در resources دارد ولی کلاسشان را تعریف نکرده.
- **رفع:** استفاده از `System.Windows.Controls.ComboBox` و `System.Windows.Controls.CheckBox` به جای `Wpf.Ui.Controls.ComboBox`.

### CS0815: Cannot assign void to implicitly-typed variable
- **رفع:** `RunEngine.Send()` از `Task` به `Task<string>` تغییر یافت + return statements اضافه شد.

### CS0103: File does not exist
- **رفع:** `System.IO.File.WriteAllText` و `System.IO.File.Exists` qualified names.

### MSB3021/MSB3027: file locked by old Ams.UI.exe
- **رفع:** ترمیم pids 14548, 18176, 20704, 21472, 22348 با `taskkill /F /PID`.

---

## باگ فیکس‌شده: duplicate KCOMBO|162+86 در Generated Script

**خط:** [ScriptGenerator.cs:124-135](src/Ams.UI/Services/ScriptGenerator.cs)

**مشکل:** وقتی `secret=true` در typeText، `TypeTextCommands` لیست دو تایی `[CLIPBOARD:text, KCOMBO|162+86]` برمی‌گرداند. `EmitStep` برای CLIPBOARD ابتدا Set-Clipboard می‌نویسد و سپس `KCOMBO|162+86`. بعد foreach وارد else می‌شود و `KCOMBO|162+86` را دوباره می‌نویسد.

**رفع:** اضافه کردن `else if (cmd == "KCOMBO|162+86") { /* already emitted */ }` بین CLIPBOARD و default.

**نتیجه قبل:** `Send-Cmd 'KCOMBO|162+86'` دو بار در خروجی `.ps1`
**نتیجه بعد:** یک بار — درست.

---

## تست‌های انجام‌شده (برنامه‌ای)

| چک | وضعیت |
|----|-------|
| Build: 0 CS errors, 0 CS warnings | ✅ |
| App runs: Ams.UI.exe starts without crash | ✅ |
| bridge.py copied to output dir | ✅ |
| WaitForSound in DLL strings | ✅ |
| CalibrateSoundThreshold in DLL strings | ✅ |
| PickRegionOnScreen in DLL strings | ✅ |
| UTF-8 BOM in generated .ps1 | ✅ |
| WSND with -TimeoutSec in generated .ps1 | ✅ |
| Set-Clipboard for secret typeText | ✅ |
| No duplicate KCOMBO|162+86 in .ps1 | ✅ |
| Sensitivity warning comment in .ps1 | ✅ |

---

## تست‌های دستی (نیاز به برد فیزیکی)

- [ ] Insert → Wait For Sound → دکمه Calibrate… نمایش داده شود
- [ ] اتصال برد (AUTO) → Calibrate → threshold پیشنهادی خوانده شود
- [ ] اجرای گام waitForSound → صدای بلند → WSND trigger شود (window 20s)
- [ ] Insert → Find Image → Pick region on screen → region انتخاب شود
- [ ] اجرای Find Image روی یک PNG واقعی
- [ ] Insert → Type Text → Sensitive تیک بخورد → log خالی از متن باشد
- [ ] Save .amsj → Open → Generate Script → محتوای .ps1 بررسی شود

---

## یادداشت فنی

- WPF-UI 3.0.5 فقط Button, TextBox, TextBlock و SymbolRegular را wrap می‌کند. ComboBox/CheckBox/TabControl از System.Windows.Controls باید مستقیم استفاده شوند.
- `<UseWindowsForms>true</UseWindowsForms>` برای System.Drawing.Point و Cursor.Position ضروری است — ambiguity را با fully-qualified names حل کردیم.
- PowerShell 5.1 encoding: UTF-8 with BOM الزامی است (`encoderShouldEmitUTF8Identifier: true`).
- `dotnet run` در Windows فایل exe را قفل می‌کند؛ قبل از build مجدد باید process را kill کنید.
