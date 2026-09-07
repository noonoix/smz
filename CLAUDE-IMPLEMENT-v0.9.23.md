# CLAUDE IMPLEMENT — v0.9.23

**موضوع:** پیش‌فرض‌های انسانی + پنجره‌ی کالیبراسیون «Measure from my hand» + مهار موس هنگام تایپ + تکمیل فوکوس هاتکی
**تاریخ:** 2026-09-01 — **پایه:** v0.9.21 (بیلد 35)
**یادداشت نسخه:** v0.9.22 فقط پرامپت بود و build نشد؛ محتوایش در v0.9.23 ادغام شده.

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن. پوشه‌های bin/obj قدیمی نگه داشته نشوند.

---

## ۱. خلاصه‌ی تغییرات (همه در زیپ اعمال شده)

### پیش‌فرض‌های انسانی (کالیبره‌شده از رکورد واقعی دست کاربر)
- `AppSettings.MouseMoveSpeedMin/Max`: 0/2300 → **150/500**
- `HumanMouse.Config.SpeedMaxPxPerSec` و fallback حالت shapeOnly → **500**
- typeText: hmin/hmax → **80/220**
- randomMousePosition: idlePauseMin/Max → **800/3000**
- مهاجرت: `AppSettings.NormalizeSpeedDefaults` — فقط 0/2300 دست‌نخورده به 150/500؛
  مقادیر سفارشی و 0/0 عمدی حفظ می‌شوند.

### کالیبراسیون شخصی
- `Services/CalibrationAnalyzer.cs` (جدید) — ریاضیات خالص: p25/p85 با clamp؛
  حداقل ۱۲ گپ کلید و ۴۰ نمونه‌ی موس، وگرنه null.
- `Views/CalibrationWindow.xaml(.cs)` (جدید) — ضبط ۲۰ ثانیه‌ای داخل برنامه.
  **حریم خصوصی:** فقط زمان‌بندی/سرعت؛ هویت کلیدها هرگز ثبت نمی‌شود.
- Options: دکمه‌های **Measure from my hand…** و **Reset to human defaults**.
- cadence تایپ در `AppSettings.TypeKeyMinMs/MaxMs` ذخیره و به
  `StepDefinitions.TypingFallbackMinMs/MaxMs` منتقل می‌شود (زنده، بدون ری‌استارت).

### مهار موس هنگام تایپ (در Parallel Group)
- سیگنال مشترک: شاخه‌ی صفحه‌کلید هر ضربه را `Interlocked` ثبت می‌کند.
- شاخه‌ی موس وقتی آخرین ضربه ≤ ۹۰۰ms است: نیم‌سرعت + مکث نامنظم ۱۲۰–۵۰۰ms
  بعد از هر ۲–۶ ضربه (و ~۱۰٪ مکث ۵۰۰–۱۲۰۰ms).
- مکث‌ها app-side و pause-aware‌اند؛ فرمان‌ها صف نمی‌شوند.

### هاتکی
- `border.Focus()` → `border.Focusable = true; Keyboard.Focus(border); e.Handled = true;`

---

## ۲. فایل‌های تغییریافته

| فایل | تغییر |
|---|---|
| `Services/DocumentService.cs` | پیش‌فرض‌ها + مهاجرت + TypeKey props |
| `Services/HumanMouse.cs` | پیش‌فرض سرعت |
| `Services/RunEngine.cs` | مهار موس + سیگنال تایپ |
| `Services/CalibrationAnalyzer.cs` | جدید |
| `Views/CalibrationWindow.xaml(.cs)` | جدید |
| `Views/OptionsDialog.xaml(.cs)` | دکمه‌ها + فوکوس هاتکی + TypeKey |
| `Models/StepDefinitions.cs` | پیش‌فرض‌ها + fallbackهای تایپ |
| `ViewModels/MainViewModel.cs` | بنر v0.9.23 + اتصال fallbackها |
| `Ams.UI.csproj` | 0.9.23 |
| `tests/TestRunner.cs` | گامهای ۲۲ و ۲۳ |
| `docs/human-defaults-calibration-v0.9.23.md` | سند کامل |

دو فایل جدید (CalibrationAnalyzer, CalibrationWindow) باید در پروژه کپی شوند —
SDK-style csproj آن‌ها را با glob می‌گیرد و csproj نیازی به ویرایش ندارد.

---

## ۳. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.23.txt
python tests\windmouse_check.py
```

---

## ۴. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] `TestRunner` — گام‌های ۱ تا ۲۳ همه PASS (گام ۲۲: ۷ assertion، گام ۲۳: ۸ assertion)
- [ ] بنر: `Classroom Studio v0.9.23 — learn-from-my-hand calibration · ...`
- [ ] منوی **Insert** شامل **Parallel Group** است
- [ ] **Tools → Options**: پیش‌فرض سرعت 150/500 دیده می‌شود؛ دکمه‌های جدید کار می‌کنند
- [ ] **Measure from my hand**: ۲۰ ثانیه تایپ + حرکت موس → نتیجه نمایش داده می‌شود →
      Apply → فیلدها پر می‌شوند → OK → در `ams-settings.json` ذخیره می‌شود
- [ ] اگر نمونه ناکافی باشد (فقط چند کلید)، پیام «not enough samples» می‌دهد و Apply غیرفعال می‌ماند
- [ ] **تب Hotkeys**: کلیک روی فیلد → کلید بلافاصله شناسایی می‌شود (فوکوس مطمئن)
- [ ] **تست موازی** («move mouse in pj6»): حین تایپ، موس کندتر و با مکث‌های نامنظم
      حرکت می‌کند؛ پس از پایان تایپ به سرعت عادی برمی‌گردد؛ بدون فریز چندثانیه‌ای و بدون پرش
- [ ] **مهاجرت:** اگر `ams-settings.json` فعلی 0/2300 دارد، بعد از یک اجرا به 150/500
      ارتقا می‌یابد؛ اگر سفارشی است، دست‌نخورده می‌ماند

---

## ۵. گزارش نهایی موردنیاز

تعداد passed/failed · خروجی تازه‌ی TestRunner · نتیجه‌ی windmouse_check ·
نتیجه‌ی تست دستی کالیبراسیون · هر تغییر اضافی با فایل و خط.
