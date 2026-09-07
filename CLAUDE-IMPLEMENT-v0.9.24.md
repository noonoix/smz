# CLAUDE IMPLEMENT — v0.9.24

**موضوع:** دیالوگ‌های فارسی (راست‌چین، گزینه‌ها انگلیسی) + کالیبراسیون مجدد سرعت از رکورد متراکم دست کاربر (300/2000)
**تاریخ:** 2026-09-01 — **پایه:** v0.9.23 (بیلد 36)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن. پوشه‌های bin/obj قدیمی نگه داشته نشوند.

---

## ۱. خلاصه‌ی تغییرات (همه در زیپ اعمال شده)

### الف) دیالوگ‌های فارسی
- `Models/StepTextsFa.cs` (**فایل جدید**) — دیکشنری توضیحات فارسی با ترتیب
  `stepType:fieldKey` ← `fieldKey` ← fallback انگلیسی.
- `Views/StepDialog.xaml.cs` — برچسب‌ها فارسی + `TextAlignment.Right`؛ CheckBoxها فارسی؛
  عنوان «New:/Edit:» ← «جدید:/ویرایش:».
- `Views/StepDialog.xaml` — OK ← «تأیید»، Cancel ← «انصراف».
- `StepDefinitions.FindTypeByFields` (جدید) — نوع استپ از مرجع Fields بدون تغییر call siteها.
- **گزینه‌ها و مقادیر Combo انگلیسی می‌مانند** (درخواست صریح کاربر).

### ب) کالیبراسیون مجدد سرعت (رکورد متراکم ۶۲۶۹ نمونه‌ای دست خود کاربر)
- سرعت دست واقعی: p25 ≈ 416 · median ≈ 980 · p75 ≈ 1970 px/s → پیش‌فرض 150/500 خیلی کند بود.
- پیش‌فرض‌ها: `MouseMoveSpeedMin/Max` = **300/2000** (AppSettings + OptionsDialog +
  HumanMouse.Config + fallback shapeOnly + دکمه‌ی Reset to human defaults).
- مهاجرت: فقط 0/2300 کارخانه → (300,2000). تنظیمات موجود کاربر دست‌نخورده.
- randomMousePosition: overshootChance 15→**25** (دست کاربر ۲/۴ بار overshoot داشت) ·
  midPauseMax 400→**500** (hesitationهای ثبت‌شده ۲۹۷–۴۸۵ms).

### ج) تصمیم مستند — wiggle رد شد
«presence wiggle» برای زنده‌ماندن نشانگر هنگام تایپ **رد شد** (نگرانی آنتی‌چیت بازی‌های
آنلاین). راه‌حل: کاربر «Hide pointer while typing» ویندوز را خاموش می‌کند. هیچ حرکت
مصنوعی اضافی در اپ نیست.

---

## ۲. نکته‌ی مهم درباره‌ی تست‌های قدیمی

سه assertion گام ۲۲ **عمداً به‌روز شدند** (پیش‌فرض 150/500 ← 300/2000) — این تغییر مستند
است، نه تضعیف تست. علت: کالیبراسیون v0.9.23 از رکورد کم‌تراکم آمده بود؛ رکورد جدید
متراکم است و سرعت واقعی دست را نشان داد. جزئیات: `docs/persian-ui-and-speed-v0.9.24.md`.

---

## ۳. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.24.txt
python tests\windmouse_check.py
```

خروجی باید شامل Step 19 تا 24 و `0 failed` باشد.

---

## ۴. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — همه‌ی گام‌ها PASS (گام ۲۲ با مقادیر 300/2000 · گام ۲۴ با ۷ assertion)
- [ ] بنر: `Classroom Studio v0.9.24 — Persian step dialogs · ...`
- [ ] منوی Insert شامل Parallel Group است

### تست دستی — دیالوگ فارسی
1. روی یک استپ (مثلاً Type Text) دابل‌کلیک کن → عنوان «ویرایش: Type Text»
2. همه‌ی توضیحات فیلدها فارسی و راست‌چین؛ مقادیر Combo انگلیسی (keystrokes/clipboard)
3. Random Mouse Position → «ناحیه X/Y»، «عرض/ارتفاع ناحیه» (نه «مختصات»)
4. Comment → برچسب «یادداشت» (نه «متن») — حل برخورد step-aware
5. OK = «تأیید» · Cancel = «انصراف»

### تست دستی — سرعت
1. اگر ams-settings.json فعلی 150/500 دارد → **حفظ می‌شود** (مهاجرت فقط برای 0/2300 است)
2. دکمه‌ی «Reset to human defaults» → 300/2000
3. حرکت موس روی صفحه باید محسوساً سریع‌تر و نزدیک‌تر به دست خودت باشد

---

## ۵. publish

همان بلوک استاندارد (تأیید `bridge\bridge.py` در خروجی + صفر فایل .cs).

## ۶. گزارش نهایی موردنیاز

passed/failed · وجود Step 19–24 · نتیجه‌ی windmouse · نتیجه‌ی تست دستی دیالوگ فارسی
(با اسکرین‌شات اگر ممکن است) · هر تغییر اضافی با فایل و خط.
