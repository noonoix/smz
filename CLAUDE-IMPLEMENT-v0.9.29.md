# CLAUDE IMPLEMENT — v0.9.29

**موضوع:** دیالوگ لوپ شفاف (فقط فیلدهای حالت فعال) + زنده‌شدن برچسب‌های فارسی per-step + فارسی‌سازی فیلدهای پوسته
**تاریخ:** 2026-09-02 — **پایه:** v0.9.28 (بیلد تأییدشده‌ی تو — ۳۰۴ پاس / ۰ فیل)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` و `tests/TestRunner.cs` و `docs/` کامل جایگزین شوند.
> این نسخه یک فایل جدید دارد: `Models/StepFieldVisibility.cs` — SDK-style است، csproj نیازی به ویرایش ندارد.

---

## ۱. چرا این نسخه

اسکرین‌شات کاربر از دیالوگ For Loop: فیلدهای count و time در هر سه حالت فعال بودند («تناقض به نظر می‌آد؟») و برچسب mode انگلیسی مانده بود.

- رفتار موتور تناقض ندارد: `mode` قانون را انتخاب می‌کند (count = تعداد / time = مدت / infinite = تا توقف دستی) و بقیه‌ی فیلدها خنثی‌اند — مشکل، نمایش همه‌ی فیلدها بود.
- باگ عمیق‌تر: `_stepType` دیالوگ از روی آرایه‌ی فیلدهای **الحاق‌شده** حدس زده می‌شد و هیچ‌وقت match نمی‌شد → تمام overrideهای فارسی per-step از v0.9.24 مرده بودند. حالا MainViewModel نوع را صریح پاس می‌دهد.

**تغییرات این درخت (اعمال‌شده — فقط build کن):**
- `FieldDef.HideUnlessValue` جدید + `StepFieldVisibility.FieldVisible` (فایل جدید) + قواعد روی سه فیلد لوپ در StepDefinitions + استفاده در ApplyConditionalVisibility.
- `StepDialog` حالا `stepType` صریح می‌گیرد (`stepType ?? FindTypeByFields`).
- `StepTextsFa`: `__name`/`__delay`/`__delayMax` فارسی (همه‌ی دیالوگ‌ها).
- بنر v0.9.29 · csproj 0.9.29 · گام ۲۹ TestRunner (۶ assertion) · `docs/loop-dialog-clarity-v0.9.29.md` · MEMORY.md.

---

## ۲. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.29.txt
python tests\windmouse_check.py
```

---

## ۳. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۲۹ همه PASS (گام ۲۹: ۶ assertion)
- [ ] بنر: `Classroom Studio v0.9.29 — clear loop dialog …`
- [ ] منوی Insert شامل Parallel Group است
- [ ] فایل `test-output-v0.9.29.txt` همراه گزارش برگردد

### تست دستی

۱. دیالوگ For Loop: در حالت **count** فقط «تعداد تکرار»، در **time** فقط «مقدار زمان + واحد زمان»، در **infinite** هیچ‌کدام دیده شود؛ برچسب mode باید فارسی باشد («حالت تکرار (count/time/infinite)») و فیلدهای پایینی هم «نام استپ / تأخیر بعد از استپ / حداکثر تأخیر».
۲. چند دیالوگ دیگر (typeText، findImage، comment) را باز کن — برچسب‌های per-step حالا باید فارسیِ متفاوت هر استپ باشند (مثلاً text در typeText «متن» و در comment «یادداشت»).
۳. پلن 2.amsj: صدا همچنان سریع (دور اول ~۱s)؛ پلن pj6: موس سالم.

---

## ۴. publish + گزارش

بلوک publish استاندارد (تأیید حیاتی `bridge\bridge.py` + صفر فایل .cs در ریلیز).
گزارش فارسی: passed/failed هر گام · وجود Step 29 · تأیید بصری دیالوگ لوپ در سه حالت + فارسی‌بودن برچسب‌ها · هر تغییر اضافی با فایل و خط.
