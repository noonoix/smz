# Human-calibrated defaults + calibration window + typing-aware suppression — v0.9.23

**تاریخ:** 2026-09-01
**نسخه:** v0.9.23 (محتوای v0.9.22 که هرگز build نشد هم در این نسخه ادغام شده)
**وضعیت:** ✅ پیاده‌سازی شد — نیازمند build و تست روی ویندوز

---

## مبنای آماری — رکورد واقعی دست کاربر

رکورد ۵۷٫۸ ثانیه‌ای (۱۲۵۵ نمونه‌ی موس، ۱۴۹ کلید) به‌عنوان استاندارد طلایی:

| معیار | مقدار انسانی |
|---|---|
| سرعت موس | median ≈ 140 px/s · p10 ≈ 63 · p90 ≈ 236 · p99 ≈ 452 |
| گام موس | median 2.24 px · cadence نمونه ~18ms |
| تله‌پورت | ۰ |
| cadence تایپ | median ≈ 204ms بین کلیدها |
| مکث موس حین تایپ | 38 بار ≥100ms در 58s · 25 بار ≥500ms · 7 بار ≥1000ms |

پیش‌فرض‌های کارخانه‌ی قبلی (0–2300 px/s، 25–70ms کلید) کاملاً بیرون از این پوشش بودند.

---

## ۱. پیش‌فرض‌های کالیبره‌شده

| جا | قدیم | جدید |
|---|---|---|
| `AppSettings.MouseMoveSpeedMin/Max` | 0 / 2300 | **150 / 500** |
| `HumanMouse.Config.SpeedMaxPxPerSec` | 2300 | **500** |
| fallback حالت shapeOnly | 150–2300 | **150–500** |
| typeText `hmin/hmax` | 25 / 70 | **80 / 220** |
| randomMousePosition `idlePauseMin/Max` | 1000 / 5000 | **800 / 3000** |
| `AppSettings.TypeKeyMinMs/MaxMs` (جدید) | — | **80 / 220** |

### مهاجرت

`AppSettings.NormalizeSpeedDefaults(min, max)`: فقط بازه‌ی دست‌نخورده‌ی کارخانه
(دقیقاً 0/2300) به 150/500 ارتقا می‌یابد. مقادیر سفارشی کاربر و 0/0 عمدی
(timing disabled) حفظ می‌شوند. یک‌بار در `Load()` اعمال و ذخیره می‌شود.

### UI

- Options: توضیح شفاف‌سازی شد («used when a step's Move Duration is 0/0; effective floor 150»).
- دکمه‌ی **Reset to human defaults** → 150/500.
- دکمه‌ی **Measure from my hand…** → پنجره‌ی کالیبراسیون.

---

## ۲. «Learn from my hand» — کالیبراسیون شخصی

### فایل‌ها

| فایل | نقش |
|---|---|
| `Services/CalibrationAnalyzer.cs` | ریاضیات خالص و تست‌پذیر |
| `Views/CalibrationWindow.xaml(.cs)` | پنجره‌ی ضبط ۲۰ ثانیه‌ای |

### طراحی

- **حریم خصوصی از نظر ساختاری:** فقط زمان‌بندی و سرعت اندازه می‌شود؛ هویت کلیدها هرگز
  ثبت نمی‌شود (برخلاف رکوردر hook سراسری). همه‌چیز داخل یک پنجره‌ی WPF است.
- تایپ در TextBox → فاصله‌ی بین کلیدها؛ حرکت موس در ناحیه‌ی مخصوص → سرعت لحظه‌ای.
- `CalibrationAnalyzer.Compute`:
  - تایپ: گپ‌های [20..1500]ms → min=p25 ، max=p85 ، clamp به [40..600]
  - موس: سرعت برای گپ‌های [4..120]ms → min=p25 ، max=p85 ، clamp به [150..2500]
  - کمتر از ۱۲ گپ کلید یا ۴۰ نمونه‌ی سرعت → null (نتیجه‌ی ناقص اعمال نمی‌شود)
- Apply → سرعت موس به فیلدهای Options می‌نشیند؛ cadence تایپ در
  `TypeKeyMinMs/MaxMs` ذخیره و به fallbackهای `StepDefinitions` منتقل می‌شود
  (به‌روزرسانی زنده، بدون ری‌استارت).

### کجاها اثر می‌گذارد

- سرعت موس: همه‌ی حرکت‌هایی که Move Durationشان 0/0 است.
- cadence تایپ: fallback برای استپ‌هایی که hmin/hmax ندارند (ایمپورت/ویرایش دستی)؛
  استپ‌های ذخیره‌شده مقادیر صریح خودشان را دارند و دست نمی‌خورند.

---

## ۳. مهار موس هنگام تایپ (Typing-aware suppression)

### مسئله

v0.9.21 صف‌شدن را حذف کرد ولی موس حین تایپ ۱۰۰٪ فعال ماند:
تأخیر p90 موس-بعد-از-کلید **۴۳ms** در برابر **۹۸۲ms** انسانی → پیوستگی غیرانسانی.

### راه‌حل

سیگنال مشترک تایپ بین شاخه‌های Parallel Group:

```csharp
private long _parallelKeySeq;          // Interlocked
private long _lastParallelKeyTick;     // Interlocked
private int  _mouseRestAtSeq = -1;     // آستانه‌ی مکث بعدی موس
```

- شاخه‌ی صفحه‌کلید بعد از هر `KTEXT|0,0,<c>` سیگنال را به‌روز می‌کند.
- شاخه‌ی موس در حلقه‌ی waypoint، اگر `TypingActiveNow()` (آخرین کلید ≤ ۹۰۰ms پیش):
  - تاخیر micro-step دو برابر می‌شود → **نیم‌سرعت** (`SuppressedMouseDelayMs`)
  - بعد از هر **۲ تا ۶ کلید**، مکث نامنظم **۱۲۰–۵۰۰ms** (و ~۱۰٪ مواقع **۵۰۰–۱۲۰۰ms**)
- مکث‌ها app-side و pause-aware هستند؛ هیچ فرمانی صف یا جابه‌جا نمی‌شود.
- با توقف تایپ (پنجره‌ی ۹۰۰ms)، موس به سرعت طبیعی برمی‌گردد.

### چیزهایی که عمداً تغییر نکردند

- مسیر غیرموازی typeText (chunkهای ۶۰ کاراکتری board-paced).
- `_mouseAnchor` — رکورد v0.9.21 صفر تله‌پورت داشت.
- پیکربندی مکث‌های موس — همان انتخاب کاربر.

---

## ۴. هاتکی — تکمیل اصلاح فوکوس

`border.Focus()` در v0.9.21 قابل‌اتکا نبود (Border پیش‌فرض Focusable نیست). حالا:

```csharp
border.Focusable = true;
Keyboard.Focus(border);
e.Handled = true;
```

---

## ۵. تست‌های رگرسیون — گام ۲۲ و ۲۳

| گام | پوشش |
|---|---|
| ۲۲ | پیش‌فرض‌های 150/500 و 80/220 · ماتریس مهاجرت (0/2300→150/500 ، حفظ سفارشی ، حفظ 0/0) · `Config.SpeedMax=500` |
| ۲۳ | پنجره‌ی ۹۰۰ms فعال‌بودن تایپ · دوبرابرشدن تاخیر بدون صفر · `CalibrationAnalyzer` روی داده‌ی مصنوعی (~125ms کلید، ~300px/s موس) · رد نمونه‌ی ناکافی |

---

## فایل‌های تغییریافته

| فایل | تغییر |
|---|---|
| `Services/DocumentService.cs` | پیش‌فرض‌ها + TypeKey props + مهاجرت |
| `Services/HumanMouse.cs` | پیش‌فرض سرعت 500 + fallback |
| `Services/RunEngine.cs` | مهار موس هنگام تایپ (855 خط) |
| `Services/CalibrationAnalyzer.cs` | **جدید** — ریاضیات کالیبراسیون |
| `Views/CalibrationWindow.xaml(.cs)` | **جدید** — پنجره‌ی ضبط |
| `Views/OptionsDialog.xaml(.cs)` | دکمه‌ها + توضیح + فوکوس هاتکی + TypeKey |
| `Models/StepDefinitions.cs` | پیش‌فرض‌های 80/220 و 800/3000 + fallbackها |
| `ViewModels/MainViewModel.cs` | بنر + اتصال fallbackهای تایپ |
| `Ams.UI.csproj` | 0.9.23 |
| `tests/TestRunner.cs` | گامهای ۲۲ و ۲۳ — ۱۵ assertion |
