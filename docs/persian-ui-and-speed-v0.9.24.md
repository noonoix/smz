# Persian step dialogs + hand-speed recalibration — v0.9.24

**تاریخ:** 2026-09-01
**نسخه:** v0.9.24
**وضعیت:** ✅ پیاده‌سازی شد — نیازمند build و تست روی ویندوز

---

## ۱. wiggle رد شد — تصمیم مستند

پیشنهاد «presence wiggle» (حرکت ۱ پیکسلی رفت‌وبرگشت برای زنده‌ماندن نشانگر هنگام تایپ)
**رد شد**: کاربر نگران حساسیت آنتی‌چیت بازی‌های آنلاین است.

**راه‌حل پذیرفته‌شده:** خاموش‌کردن «Hide pointer while typing» در ویندوز
(Settings → Bluetooth & devices → Mouse → Additional mouse settings → Pointer Options).
هیچ حرکت مصنوعی اضافی در اپ ساخته نمی‌شود.

---

## ۲. کالیبراسیون مجدد سرعت — از رکورد متراکم دست کاربر

### داده‌ی جدید (Record Being Edited — ۶۲۶۹ نمونه در ۱۸٫۲ ثانیه، خودِ کاربر)

رکورد قبلی (gold standard v0.9.23) خروجی کم‌تراکم بود (~۱۸ms بین نمونه‌ها) و سرعت را
دست‌کم می‌گرفت. رکورد جدید متراکم است (~۱ms) و با پنجره‌ی هموارسازی ۴۰ms برای حذف لرزش:

| معیار | مقدار |
|---|---|
| سرعت حرکت (smoothed) | p10 ≈ 128 · **p25 ≈ 416** · median ≈ 980 · **p75 ≈ 1970** · p90 ≈ 2840 px/s |
| حرکت هدف‌دار کوتاه | ۱۴۸px در ۲۴۴ms ≈ ۶۲۹ px/s |
| مسیرهای طولانی (wandering) | ~۱۰۵۷–۱۲۸۲ px/s path-speed |
| مکث‌ها | ≥100ms ≈ ۴۰/min · ≥250ms ≈ ۲۰/min · ≥500ms هیچ (نمونه‌ی کوتاه فعال) |
| طول مکث‌های hesitation | ۲۹۷–۴۸۵ms |
| overshoot | ۲ از ۴ حرکت (نمونه کم — نشانه‌ی قوی) |

نتیجه: پیش‌فرض v0.9.23 (۱۵۰–۵۰۰ px/s) دو تا شش برابر کندتر از دست واقعی کاربر بود.

### مقادیر جدید

| جا | قدیم | جدید |
|---|---|---|
| `AppSettings.MouseMoveSpeedMin/Max` (کارخانه) | 150 / 500 | **300 / 2000** |
| `HumanMouse.Config.SpeedMaxPxPerSec` | 500 | **2000** |
| fallback حالت shapeOnly | 500 | **2000** |
| OptionsDialog پیش‌فرض‌ها + دکمه‌ی Reset | 150 / 500 | **300 / 2000** |
| مهاجرت `NormalizeSpeedDefaults(0,2300)` | →(150,500) | →**(300,2000)** |
| randomMousePosition `overshootChance` | 15 | **25** (دست کاربر ۲/۴ بار overshoot داشت) |
| randomMousePosition `midPauseMax` | 400 | **500** (hesitationهای ثبت‌شده ۲۹۷–۴۸۵ms) |

**بدون مهاجرت اجباری:** تنظیمات موجود کاربر (150/500 یا کالیبره‌شده) دست نمی‌خورد؛
فقط کارخانه‌ی 0/2300 دست‌نخورده به مقادیر جدید می‌رسد. کاربر می‌تواند با دکمه‌ی
«Reset to human defaults» خودش به 300/2000 برود.

**تغییرنیافتنده‌ها:** کف سخت‌گیرانه‌ی ۱۵۰ px/s (ضد stall) · تایپ 80/220 · آستانه‌های
مهار موس v0.9.23 · منحنی 15–45 (نمونه‌ی ۴ تایی برای قضاوت کافی نیست).

---

## ۳. دیالوگ‌های فارسی

درخواست کاربر: «گزینه‌ها انگلیسی باشند ولی توضیحات فارسی» + راست‌چین.

### معماری — `Models/StepTextsFa.cs` (جدید)

```csharp
StepTextsFa.Get(stepType, fieldKey, englishFallback)
```

ترتیب جست‌وجو: `stepType:fieldKey` ← `fieldKey` ← برچسب انگلیسی اصلی.
برخوردهای کلیدی (text/mode/path/x/y/w/h/label/holdMin…) با نسخه‌ی step-aware حل می‌شوند.
مقادیر Combo و گزینه‌ها دست‌نخورده و انگلیسی می‌مانند.

### اتصال — `Views/StepDialog.xaml(.cs)`

- `StepDefinitions.FindTypeByFields(fields)` — نوع استپ از روی مرجع مشترک آرایه‌ی
  Fields پیدا می‌شود؛ **call siteها تغییر نکردند**.
- برچسب فیلدها: فارسی + `TextAlignment.Right` (راست‌چین RTL).
- CheckBoxها: متن فارسی.
- عنوان پنجره: «New: X» ← «جدید: X» · «Edit: X» ← «ویرایش: X»
- دکمه‌ها: OK ← تأیید · Cancel ← انصراف
- نام اکشن‌ها و مقادیر گزینه‌ها انگلیسی می‌مانند (طبق درخواست).

**خارج از scope عمدی:** دیالوگ‌های خاص (SearchPictureDialog، RegionPicker، Options)
متن انگلیسی خودشان را دارند — اگر خواستی نسخه‌ی بعد همان الگو روی آن‌ها هم می‌آید.
خلاصه‌ی استپ‌ها در درخت اصلی هم انگلیسی می‌ماند (ردیف وضعیت فشرده است، نه توضیح).

---

## ۴. تست‌ها

**گام ۲۲ (به‌روز — مستند):** سه assertion پیش‌فرض سرعت به 300/2000 به‌روز شدند
(تغییر عمدی پیش‌فرض، طبق قانون پروژه مستند شد).

**گام ۲۴ (جدید — ۷ assertion):** وجود متن فارسی برای کلید مشترک · حل برخورد step-aware ·
کارکردن بدون stepType · fallback انگلیسی برای کلید ناشناخته · FindTypeByFields ·
پیش‌فرض overshoot ۲۵ · پیش‌فرض midPauseMax ۵۰۰.

---

## فایل‌های تغییریافته

| فایل | تغییر |
|---|---|
| `Models/StepTextsFa.cs` | **جدید** — لایه‌ی فارسی |
| `Models/StepDefinitions.cs` | FindTypeByFields + overshoot 25 + midPauseMax 500 |
| `Views/StepDialog.xaml(.cs)` | برچسب‌های فارسی راست‌چین + عنوان + دکمه‌ها |
| `Services/DocumentService.cs` | پیش‌فرض‌های 300/2000 + هدف مهاجرت |
| `Services/HumanMouse.cs` | Config پیش‌فرض 2000 + fallback |
| `Views/OptionsDialog.xaml(.cs)` | پیش‌فرض‌ها + Reset + متن راهنما |
| `ViewModels/MainViewModel.cs` | بنر v0.9.24 |
| `Ams.UI.csproj` | 0.9.24 |
| `tests/TestRunner.cs` | گام ۲۴ + به‌روزرسانی مستند گام ۲۲ |
