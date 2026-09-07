# CLAUDE IMPLEMENT — v0.9.25

**موضوع:** پوشش کامل فارسی در همه‌ی بخش‌ها (دیالوگ Find Image، Options، Region Picker، کالیبراسیون، Play Options، Inspector، تولتیپ‌ها، پیام‌های کد)
**تاریخ:** 2026-09-01 — **پایه:** v0.9.24 (بیلد تأییدشده‌ی تو)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن.

---

## ۱. چرا این نسخه

gزارش کاربر: «v0.9.24 بطور کامل فارسی نشده — همه توضیحات فیلدها در همه بخش‌ها».
لایه‌ی v0.9.24 فقط StepDialog عمومی را پوشش می‌داد. این نسخه بقیه را می‌پوشاند:

- **SearchPictureDialog** (Find Image) — همه‌ی هدرها/برچسب‌ها/دکمه‌ها/Comboها/تولتیپ‌ها فارسی.
  Comboها index-نگاشت هستند → ترجمه‌ی متن نمایشی پلن‌های ذخیره‌شده را نمی‌شکند (ترتیب ثابت ماند).
- **OptionsDialog** — تب‌ها + همه‌ی برچسب‌ها + ردیف‌های هاتکی (اجرا/توقف/مکث/ادامه).
- **RegionPickerWindow** · **CalibrationWindow** · **MainWindow** (Play Options + Inspector +
  لاگ سریال + تولتیپ‌های ریل + دکمه‌های مکث/ادامه) · **StepDialog** (دکمه‌های
  Calibrate/Browse/Pick region + پیام اعتبارسنجی) · **MainViewModel** (عنوان batch + خطاهای فایل).

**قانون حفظ‌شده:** گزینه‌ها/مقادیر/واحدها (ms, second, entireScreen, keystrokes…) و نام
اکشن‌ها و منوها انگلیسی می‌مانند.

**تغییرات کدِ فراتر از متن:**
- `StepDefinitions.All` (readonly enumerate — برای sweep تست)
- `StepTextsFa.Has(stepType, key)` (bool پوشش — برای sweep تست)
- در StepDialog.xaml کامنت‌های داخل تگ قبلاً حذف شده‌اند (همان اصلاح MC3000 تو در این درخت هست).

---

## ۲. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.25.txt
python tests\windmouse_check.py
```

---

## ۳. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۲۵ همه PASS (گام ۲۵: ۷ assertion)
- [ ] بنر: `Classroom Studio v0.9.25 — full Persian UI · ...`
- [ ] منوی Insert شامل Parallel Group است

### تست دستی — چک‌لیست فارسی (همه‌ی بخش‌ها)

۱. **Find Image** (مهم‌ترین): باز کن → «تصویری که باید جست‌وجو شود» · «درصد شباهت:» ·
   «کجا جست‌وجو شود» · «وقتی تصویر پیدا شد چه شود» · دکمه‌ها فارسی · Comboها جمله‌های فارسی
   (واحدها ms/second انگلیسی می‌مانند) · OK=«تأیید» Cancel=«انصراف»
۲. **Type Text** (دیالوگ عمومی): برچسب‌ها فارسی راست‌چین — از v0.9.24
۳. **Tools → تنظیمات**: تب‌ها «سریال / پخش / هاتکی‌ها» · «پوشه‌ی Python» ·
   «اندازه‌گیری از دست من…» · «بازنشانی به پیش‌فرض انسانی»
۴. **پنجره‌ی اصلی**: «گزینه‌های پخش» · «بازرس» · «لاگ سریال» · تولتیپ ریل فارسی
۵. **کالیبراسیون**: «یادگیری از دست من» — متن‌ها و دکمه‌ها فارسی
۶. **Region Picker**: راهنمای بالای صفحه فارسی
۷. یک پلن قدیمی باز کن و ذخیره کن — **Comboهای Find Image باید مقادیر درست را حفظ کنند**
   (index-نگاشت؛ اگر یک پلن ذخیره‌شده‌ی قدیمی باز شود و مقادیرش درست نمایش داده شود یعنی سالم است)

---

## ۴. publish + گزارش

بلوک publish استاندارد (تأیید `bridge\bridge.py` + صفر فایل .cs).
گزارش: passed/failed · وجود Step 19–25 · اسکرین‌شات از دیالوگ Find Image فارسی اگر ممکن است ·
نتیجه‌ی باز/ذخیره‌ی یک پلن قدیمی (پایداری Comboها) · هر تغییر اضافی با فایل و خط.
