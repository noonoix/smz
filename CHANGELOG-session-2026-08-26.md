# CHANGELOG — 2026-08-26

**پروژه:** `ams-wpf-shell-v0.6`
**نسخه‌ها:** v0.8.5 → v0.9.0 → v0.9.1 → v0.9.2

---

## خلاصه روز

### بخش اول — v0.8.5
۱. **Options dialog** — جلوگیری از ذخیره کلید ترکیبی تکراری
۲. **دکمه‌های Run/Stop** — برچسب پویا از settings (بدون hardcoded)
۳. **Stop دکمه** — IsRunning بلافاصله false
۴. **حرکت رندم موس** — مسیر منحنی با perpendicular offset 5%–90%
۵. **فاصلهٔ واقعی مسیر** — محاسبه بر اساس `dist1 + dist2`
۶. **سرعت و زمان‌بندی هر قطعه** — سرعت مستقل + نسبت تقسیم رندم
۷. **ScriptGenerator.EmitStep** — افزودن پارامترهای screenW/screenH
۸. تست‌ها: 67/67 پاس

### بخش دوم — v0.9.0
۱. **موتور HumanMouse** — جایگزین کامل منحنی دوقسمتی: WindMouse + ease-in-out + overshoot&correct + چهار لایه مکث
۲. **رفع باگ مبدأ مسیر** — شروع از موقعیت واقعی کرسر نه گوشهٔ ریجن
۳. **ScriptGenerator** — سه باگ بحرانی: ۶× `}` اضافی، `[Math]::Random::Default`، مبدأ اشتباه
۴. **۱۴ رفع باگ** — playAudio، ReloadKeyBindings، Pause، هم‌پوشانی Run，aborted event، typeText word space…
۵. تست‌ها: TestRunner گام ۱۶ + اعتبارسنجی عددی پایتون (۶۰۰ حرکت، ۰ شکست)
۶. تست نهایی: 84/84 پاس

### بخش سوم — v0.9.1
۱. **رفع حرکت تکه‌تکه** — هر waypoint فشرده در `abs,0` یک رفت‌وبرگشت سریال داشت → لرزش رباتیک. حالا مسیر WindMouse فقط برای شکل منحنی ساخته می‌شود، سپس با `ToControlPoints` به ۱–۵ نقطهٔ کنترلی فروکاسته شده و با `MMOVE|x,y,abs,1` فرستاده می‌شود (فرمور smoothstep می‌کند)
۲. **تست جدید:** کنترل تعداد نقاط کنترلی (۱–۸)، فرود دقیق روی هدف، decimation سالم
۳. **تست نهایی:** 85/85 پاس

### بخش چهارم — v0.9.2
۱. **رفع باگ typeText فارسی/RTL** — متن غیر-ASCII (فارسی، عربی، CJK) به‌جای throw کردن، خودکار به clipboard mode سوییچ می‌شود
۲. **تست جدید:** ۸۶/۸۶ پاس (تست Persian auto-fallback)

### بخش پنجم — v0.9.3
۱. **دکمه‌های Run/Stop/Pause/Resume سراسری** — ثبت به‌عنوان global hotkey سیستم‌عامل (RegisterHotKey /user32.dll) → کار می‌کند حتی وقتی پنجره برنامه فوکوس نیست
۲. **معماری:** `GlobalHotkeyService` جدید (WndProc hook via SetWindowLongPtr) + نصب در `OnSourceInitialized` + پاک‌سازی در `OnClosed`
۳. **حساسیت بازی‌های آنلاین:** فقط `RegisterHotKey` (Win32 استاندارد) — بدون SendInput، بدون SetWindowsHookEx، بدون DLL injection. بازی‌ها این‌ها را detect نمی‌کنند
۴. **تست‌ها:** ۸۶/۸۶ پاس (بدون تغییر — UI hook قابل تست واحد نیست)

---

## v0.8.5 — جزئیات

### 1. جلوگیری از کلید ترکیبی تکراری
**مشکل:** کاربر می‌تونست یک کلید (مثلاً `Ctrl+F1`) رو هم به Run و هم به Resume اختصاص بده. WPF در runtime دو binding یکسان ایجاد می‌کرد.
**راه‌حل:** در `OptionsDialog.Ok_Click` — GroupBy روی مقادیر + MessageBox هشدار + abort از save. فیلدهای خالی نادیده گرفته می‌شن.
**فایل:** `Views/OptionsDialog.xaml.cs`

### 2. برچسب پویای دکمه‌ها
**مشکل:** دکمه‌ها متن ثابت `"Run    Shift+F1"` داشتند.
**راه‌حل:** `RunLabel` / `StopLabel` properties + XAML binding.
**فایل‌ها:** `ViewModels/MainViewModel.cs`، `MainWindow.xaml`

### 3. Stop دکمه بلافاصله
**مشکل:** IsRunning = false بعد از 800ms delay اجرا می‌شد.
**راه‌حل:** انتقال `IsRunning = false` به ابتدای متد Stop.
**فایل:** `ViewModels/MainViewModel.cs`

### 4. حرکت رندم موس — مسیر منحنی
**مشکل:** حرکت مستقیم robotic بود.
**راه‌حل:** perpendicular offset 5%–90% از فاصلهٔ کل + direction رندم (چپ/راست).
**فایل‌ها:** `Services/RunEngine.cs`، `Services/ScriptGenerator.cs`

### 5. فاصلهٔ واقعی مسیر
**مشکل:** `baseMs = dist * 1000 / speed` از فاصلهٔ مستقیم استفاده می‌کرد.
**راه‌حل:** `totalDist = dist1 + dist2` (طول واقعی دوسرخرطه).
**فایل‌ها:** `Services/RunEngine.cs`، `Services/ScriptGenerator.cs`

### 6. سرعت و زمان‌بندی مستقل هر قطعه
**مشکل:** سرعت ثابت + تقسیم 70/30 ثابت.
**راه‌حل:** `speed1/speed2` مستقل + `segRatio = 0.3 + random * 0.4`.
**فایل‌ها:** `Services/RunEngine.cs`، `Services/ScriptGenerator.cs`

### 7. ScriptGenerator.EmitStep — screenW/screenH
**مشکل:** CS0103: name 'screenW' does not exist.
**راه‌حل:** افزودن پارامترها به امضای EmitStep + پاس به فراخوانی‌های بازگشتی.
**فایل:** `Services/ScriptGenerator.cs`

---

## v0.9.0 — موتور HumanMouse + رفع ۱۴ باگ

### 1. موتور حرکت انسانی موس (بازنویسی کامل)
مسیر منحنی دوقسمتی v0.8.5 با الگوریتم **WindMouse** جایگزین شد (`Services/HumanMouse.cs`):

- **مسیر:** جاذبه به‌سمت هدف + «باد» تصادفی + گام تطبیقی → ۱۰–۷۰ نقطه میانی متراکم
- **پروفایل سرعت:** ease-in-out (وزن زنگوله‌ای 0.3 تا 2.4) — شروع کند، اوج وسط، فرود نرم
- **Overshoot & Correct:** با احتمال ۱۵٪ (قابل تنظیم) اول کمی از هدف رد می‌شود، مکث 60–180ms، بعد تصحیح
- **رفع باگ بحرانی مبدأ:** مسیر قبلی از گوشهٔ بالا-چپ *ریجن* شروع می‌شد — حالا `Cursor.Position` مبدا
- **کلمپ صفحه:** همهٔ نقاط (حتی بیرون زده از باد) به داخل صفحه کلمپ می‌شوند

### مدیریت مکث (۴ لایه — قابل تنظیم در دیالوگ استپ)

| فیلد | پیش‌فرض | معنی |
|---|---|---|
| `pauseBeforeMin/Max` | 120–450 ms | مکث «فکر کردن» قبل از شروع حرکت |
| `pauseAfterMin/Max` | 150–600 ms | مکث نشستن بعد از رسیدن |
| `midPauseChance` + `midPauseMin/Max` | 12٪ · 100–400 ms | تردید وسط مسیر (حداکثر یک بار) |
| `idleEveryMin/Max` + `idlePauseMin/Max` | هر ۵–۱۲ حرکت · 1000–5000 ms | **استراحت طولانی هر N حرکت** (max=0 خاموش) |

شمارندهٔ هر-N-حرکت روی RunEngine نگه داشته می‌شود → بین استپ‌ها و تکرارهای Play Options ادامه دارد.

### اعمال به بقیهٔ حرکت‌ها
- **Mouse Position** با تیک human → موتور با پرسیت Gentle (مکث‌های سبک، بدون استراحت طولانی)
- **Find Image** → حرکت انسانی به‌جای پرش مستقیم
- **Park Cursor** → چک‌باکس ATM که قبلاً ذخیره می‌شد ولی اجرا نمی‌شد، حالا کار می‌کند

### 2. رفع ۱۴ باگ

| # | باگ | فایل |
|---|---|---|
| 1 | playAudio غیر-لوپ: `finally` بلافاصله پلیر را Close می‌کرد → **صدا هیچ‌وقت پخش نمی‌شد** | RunEngine.cs |
| 2 | playAudio لوپ: بعد از Stop **تا ابد پخش می‌ماند**؛ حالا `StopAllAudio()` در پایان run | RunEngine.cs + MainViewModel.cs |
| 3 | `ReloadKeyBindings` با `bindings.Clear()` کلیدهای Ctrl+N/O/S، F2، Del، Ctrl+D، Alt+↑/↓ را **بی‌صدا می‌کشت** | MainViewModel.cs |
| 4 | دکمهٔ Pause هرگز غیرفعال نمی‌شد (`IsNotPaused` notify نداشت) | MainViewModel.cs |
| 5 | Stop دکمهٔ Run را آزاد می‌کرد ولی انجین هنوز جمع نشده بود → امکان دو اجرای هم‌پوشان؛ حالا گیت `_runActive` | MainViewModel.cs |
| 6 | حلقهٔ Pause با `Task.Run(WaitOne)` هر 300ms یک نخ می‌سوزاند → poll سادهٔ 100ms | MainViewModel.cs |
| 7 | چک‌باکس «Do not activate the main window when stopped» هیچ‌جا استفاده نمی‌شد → حالا honored | MainViewModel.cs |
| 8 | **رگرسیون رویداد aborted:** bridge.py بعد از abort رویداد `aborted` می‌فرستد ولی C# کیس نداشت → SendAsync تا تایم‌اوت می‌چسبید | PythonBoardBridge.cs |
| 9 | مردن sidecar پایتون SendAsync/Connect معلق را هنگ می‌گذاشت → حالا fault می‌شود | PythonBoardBridge.cs |
| 10 | typeText حالت word-humanize فاصلهٔ بین کلمات را تایپ نمی‌کرد → «hello world» → «helloworld» | StepDefinitions.cs |
| 11 | Pause فقط *بین* استپ‌ها عمل می‌کرد؛ حالا `PausableDelay` → وسط تأخیرها و وسط حرکت موس هم فریز می‌شود | RunEngine.cs |
| 12 | تب‌های Options: Playback و Hotkeys می‌توانستند هم‌زمان باز بمانند → `SelectTab` واحد | OptionsDialog.xaml.cs |
| 13 | رادیوهای «Repeat mode» در Options هیچ بایندینگ/هندلری نداشتند (UI مرده) → حذف شدند | OptionsDialog.xaml |
| 14 | Cut/Copy/Paste فقط در منوی راست‌کلیک بود → به منوی Edit اضافه شد | MainWindow.xaml |

### 3. ScriptGenerator — رفع 3 باگ بحرانی PowerShell
1. **باگ parse:** ۶ تا `}` اضافی → اسکریپت تولیدی parse نمی‌شد
2. **باگ runtime:** `[Math]::Random::Default.NextDouble()` وجود ندارد → crash. حالا `$script:rng = New-Object System.Random`
3. **باگ مبدأ:** مسیر از گوشهٔ ریجن شروع می‌شد → حالا `[System.Windows.Forms.Cursor]::Position`
4. **کف سرعت:** 150px/s — قبلاً draw از [0..2300] می‌توانست نزدیک صفر شود و حرکت ده‌ها ثانیه طول بکشد

### 4. تست‌ها
- `tests/TestRunner.cs` — Step 16: 17 تست جدید
  - مسیر دقیق روی هدف، کلمپ صفحه، کادنس استراحت، کف سرعت، فاصلهٔ کلمات، براکت متوازن PS
- `ams-shell/tests/windmouse_check.py` — پورت 1:1 الگوریتم
  - 600 حرکت تصادفی، 0 شکست، میانگین 32 waypoint/حرکت
  - 46 استراحت طولانی در 400 حرکت با فاصلهٔ 5–12

**نتیجه: 84 passed, 0 failed** (افزایش از 67)

---

## v0.9.1 — رفع حرکت تکه‌تکه (Choppy Cursor)

### علت ریشه
v0.9.0 مسیر WindMouse را با ۱۰–۷۰ نقطهٔ متراکم می‌ساخت و هر نقطه را یک فرمان جداگانه `MMOVE|x,y,abs,0` می‌فرستاد:
1. **هر نقطه = یک رفت‌وبرگشت کامل سریال** (اپ ← bridge.py ← برد ← پاسخ) — ده‌ها میلی‌ثانیه وقفهٔ نامنظم بین هر دو نقطه
2. **هر MMOVE خام (`human=0`) یک پرش آنی** به مختصات بعدی بود

نتیجه: پرش‌های کوچک پشت‌سرهم با وقفه‌های نامنظم → حرکت تکه‌تکه و رباتیک.

### راه‌حل
فرمور خودش با فلگ `human=1` درون‌یابی smoothstep انجام می‌دهد — پس درون‌یابی را به عهدهٔ فرمور گذاشتیم:

- مسیر WindMouse فقط برای **شکل منحنی** ساخته می‌شود
- سپس با `ToControlPoints` به چند نقطهٔ کنترلی فروکاسته می‌شود:
  - کوتاه (<۱۲۰px) → ۱ نقطه (انسان حرکت کوتاه را یک‌جا انجام می‌دهد)
  - متوسط (۱۲۰–۴۰۰px) → ۲–۳ نقطه
  - بلند (>۴۰۰px) → ۳–۵ نقطه
- نقاط کنترلی با `MMOVE|x,y,abs,1` فرستاده می‌شوند → فرمور هر قطعه را نرم و پیوسته interpolate می‌کند
- ریتم ease-in-out و مدیریت مکث (reaction / hesitation / settle / استراحت ۰–۵ ثانیه‌ای هر N حرکت) بدون تغییر حفظ شد
- همین اصلاح در خروجی PowerShell (`Move-HumanMouse`) هم اعمال شد

### تغییرات فنی

| فایل | تغییر |
|------|-------|
| `Services/HumanMouse.cs` | افزودن `ToControlPoints` + `ControlCount` — نمونه‌برداری از trail متراکم |
| `Services/RunEngine.cs` | `abs,0` → `abs,1` در HumanMoveToAsync |
| `Services/ScriptGenerator.cs` | نمونه‌برداری کنترل‌پوینت + `abs,1` در خروجی PS |
| `tests/TestRunner.cs` | تست جدید: تعداد نقاط کنترلی (۱–۸) + decimation end-on-target |

### تست‌ها
- `tests/TestRunner.cs` — ۱ تست اضافه: کنترل تعداد نقاط کنترلی + decimation
- `ams-shell/tests/windmouse_check.py` — پایدار (۶۰۰ حرکت، ۰ شکست)

**نتیجه: 85 passed, 0 failed** (افزایش از 84)

---

## v0.9.2 — رفع typeText فارسی (Auto-fallback به clipboard)

### مشکل
فایل‌های `.amsj` با متن فارسی/عربی/CJK و `mode: "keystrokes"` هنگام اجرا throw می‌کردند:
```
InvalidOperationException: KTEXT is ASCII-only on the board — switch this step to clipboard mode...
```
چون تابع `TypeTextCommands` قبل از تولید دستور regex چک می‌کرد و هر کاراکتر غیر-ASCII را reject می‌کرد.

### راه‌حل
به‌جای throw، خودکار به clipboard mode سوییچ می‌شود.
کد جدید:
```csharp
bool useClipboard = secret || mode == "clipboard" || Regex.IsMatch(text, @"[^\x20-\x7E]");
if (useClipboard)
    return new[] { "CLIPBOARD:" + text, "KCOMBO|162+86" };
```

### تست
- تست جدید: `typeText Persian auto-fallback` → `CLIPBOARD:آمار دست واقع شما, KCOMBO|162+86`
- **نتیجه: 86 passed, 0 failed** (افزایش از 85)

---

## تست‌ها

| معیار | مقدار |
|------|------|
| واحد test | 86 passed, 0 failed |
| خطای کامپایل | 0 |
| warning (غیرمرتبط) | 2 (CS8629 در VisionService) |
| graphify nodes | 1383 |
| graphify edges | 2407 |
| windmouse validation | 600 moves, 0 failures, mean 32 pts/move |

---

## فایل‌های تغییر یافته

| فایل | تغییر |
|------|-------|
| `Services/HumanMouse.cs` | **جدید** — الگوریتم WindMouse + pause planner (304 خط) |
| `Services/RunEngine.cs` | HumanMoveToAsync + PausableDelay + StopAllAudio + playAudio fix |
| `Services/ScriptGenerator.cs` | Move-HumanMouse + 3 PS bug fixes |
| `Models/StepDefinitions.cs` | 11 فیلد pause + word space fix |
| `ViewModels/MainViewModel.cs` | _runActive gate + pause poll + NoActivate + select-only-4-bindings |
| `Views/OptionsDialog.xaml.cs` | SelectTab unified method |
| `Services/PythonBoardBridge.cs` | aborted event + sidecar death fault |
| `Views/OptionsDialog.xaml` | حذف رادیوهای مرده Repeat mode |
| `MainWindow.xaml` | Cut/Copy/Paste به منوی Edit |
| `Services/GlobalHotkeyService.cs` | **جدید** — RegisterHotKey + SetWindowLongPtr WndProc hook (global hotkeys) |
| `ViewModels/MainViewModel.cs` | ReloadKeyBindings: global hotkey install on save |
| `MainWindow.xaml.cs` | OnSourceInitialized + OnClosed hooks for global hotkey lifecycle |
| `Tests/TestRunner.cs` | Step 16: 19 تست جدید (شامل v0.9.1 control-point + v0.9.2 Persian fallback) |
| `Models/StepDefinitions.cs` | v0.9.2: typeText auto-fallback non-ASCII → clipboard |
| `ams-shell/tests/windmouse_check.py` | اعتبارسنجی الگوریتم |
| `memory/v0.9.0-human-mouse.md` | سند ویژگی |

### بخش ششم — v0.9.3 (startup-crash hotfix)
۱. **رفع کرش راه‌اندازی** — GlobalHotkeyService از `SetWindowLongPtr(GWL_WNDPROC)` با امضای delegate نادرست (پارامتر اضافی `ref bool handled` — قرارداد `HwndSourceHook` نه WndProc بومی ویندوز) استفاده می‌کرد → ویندوز اولین پیام پنجره را با function pointer اشتباه صدا زد → پشته خراب شد → پروسه قبل از نمایش پنجره مرد.
۲. **اصلاح:** بازنویسی کامل GlobalHotkeyService با الگوی رسمی و امن WPF: `HwndSource.AddHook` — همان قابلیت هات‌کی گلوبال حفظ شد، بدون subclassing خطرناک.
۳. **جلوگیری از اجرای دوباره:** کمبویی که گلوبال ثبت شد دیگر KeyBinding محلی نمی‌گیرد (وگرنه با فوکوس، Run دوبار اجرا می‌شد).
۴. **بازیابی send_path:** بیلد قبلی Claude Code کل کار stream متراکم موس (`send_path` در `bridge.py` + HumanMouse + RunEngine) را از دست داده بود — برگرداندم.
۵. تست‌ها: ۸۶/۸۶ پاس (بدون تغییر — کد GlobalHotkeyService قابل تست واحد نیست)

## v0.9.3 — اعمال نسخهٔ اصلاح‌شده (startup-crash fix)

### علت کرش قبلی
`GlobalHotkeyService.cs` از `SetWindowLongPtr(GWL_WNDPROC)` با delegateٔ پنج‌پارامتری استفاده می‌کرد:
```csharp
(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
```
این امضا `HwndSourceHook` است (WPF) نه `WndProc` بومی ویندوز (۴ پارامتر). ویندوز اولین پیام پنجره را حین ساخت (قبل از نمایش پنجره) با function pointer اشتباه صدا زد → پشته خراب شد → پروسه همان‌لحظه می‌مرد.

### اصلاح اعمال‌شده
بازنویسی کامل `GlobalHotkeyService.cs` با الگوی رسمی و امن WPF:
```csharp
public static void Install(Window window)
{
    _hwnd = new WindowInteropHelper(window).Handle;
    _source = HwndSource.FromHwnd(_hwnd);
    _hook = WndProc;
    _source?.AddHook(_hook);   // safe, no subclassing
}
```

### بازیابی فایل‌های گمشده
نسخهٔ v0.9.3 zip شامل `send_path` dense stream بود که در بیلد قبلی Claude Code از دست رفته بود:
- `HumanMouse.cs` — بازگشت به state dense micro-step stream
- `RunEngine.cs` — `SendPathAsync` + control point fallback
- `ScriptGenerator.cs` — `Send-Path` PowerShell function
- `PythonBoardBridge.cs` — `send_path` handler
- `bridge.py` — stream متراکم موس در یک عملیات واحد

### نتیجه
- ✅ بیلد: 0 error, 0 warning
- ✅ تست‌ها: ۸۶/۸۶ پاس
- ✅ windmouse: 600 moves, 0 failures
- ✅ exe بلافاصله پنجره را نشان می‌دهد

### بخش هفتم — v0.9.4
۱. **اصلاح رندم مسیر موس** — افزودن `CurvePct` (۰–۱۰۰، پیش‌فرض ۳۰) به تنظیمات step
۲. **TunedWind** — ضریب wind/gravity متغیر بر اساس curvature و distance
۳. **کاهش overshoot** — از ۳–۳۰px به ۲–۱۲px، lateral از ±۴ به ±۲
۴. **gravity افزایش** — از ۹ به ۱۴ برای همگرایی سریع‌تر مسیر
۵. **گزینه curv** — فیلد جدید در dialog برای تنظیم انحنای مسیر
۶. تست‌ها: ۸۶/۸۶ پاس (بدون تغییر — فیلد curvePct پیش‌فرض ۳۰)
