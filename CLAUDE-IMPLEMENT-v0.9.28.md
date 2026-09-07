# CLAUDE IMPLEMENT — v0.9.28

**موضوع:** تشخیص فوری تصویر در entireScreen — گرم‌کردن vision + دور اول همیشه‌جست‌وجو + تایم‌اوت/Stop بین نوارها
**تاریخ:** 2026-09-02 — **پایه:** v0.9.27 (بیلد تأییدشده‌ی تو — ۳۰۱ پاس / ۰ فیل؛ اصلاح MediaEnded-scope ات هم در TestRunner مرج شده)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن.

---

## ۱. چرا این نسخه

گزارش کاربر: با پلن 2.amsj جدید صدا ~۱۵ ثانیه بعد از دیده‌شدن تصویر پخش شد، حتی بعد از v0.9.27.

شواهد: diff پلن نشان داد `searchScope: region → entireScreen`. در entireScreen هر دور جست‌وجو = ۴ نوار تمام‌صفحه × (کپچر + انتگرال‌ایمیج‌ها + NCC هرمی + refine) و دور اول سرد (tier-0 JIT + LOH) ≈ ~۱۵s؛ تایم‌اوت فقط بین دورها چک می‌شد و skip تصادفی ۳۰٪ می‌توانست قالب را از دور اول حذف کند. ریشه‌ی v0.9.27 (MediaPlayer روی dispatcher) برای ران قدیم region-based درست بود و ثابت می‌ماند؛ این یکی vision-side است.

**تغییرات این درخت (اعمال‌شده — فقط build کن):**
- `VisionService.Warmup()` جدید + فراخوانی آن در ابتدای `RunAsync` (RunEngine).
- skip تصادفی ۳۰٪ فقط بعد از دور اول (`polls > 0 &&`).
- چک `ct` و تایم‌اوت بین نوارهای جست‌وجو (Stop/timeout دیگر وسط دور گیر نمی‌کنند).
- لاگ `poll round N took X ms` برای شواهد ران بعدی.
- بنر v0.9.28 · csproj 0.9.28 · گام ۲۸ TestRunner (۵ assertion؛ اولیش Warmup اجرایی واقعی است) · `docs/vision-warmup-v0.9.28.md` · MEMORY.md.

---

## ۲. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.28.txt
python tests\windmouse_check.py
```

---

## ۳. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۲۸ همه PASS (گام ۲۸: ۵ assertion)
- [ ] بنر: `Classroom Studio v0.9.28 — instant vision detection …`
- [ ] منوی Insert شامل Parallel Group است
- [ ] فایل `test-output-v0.9.28.txt` همراه گزارش برگردد

### تست دستی

۱. **پلن 2.amsj (entireScreen):** از شروع run تا «find image: HIT» و شنیدن صدا باید زیر ~۱–۲s باشد (قبلاً ~۱۵s). خط لاگ `poll round 1 took … ms` را از لاگ سریال بخوان و عددش را در گزارش بفرست — این شاهد قطعی رفع است.
۲. اگر جای ظاهرشدن تصویر ثابت است، region کوچک بگذار — یک مرتبه‌ی بزرگی ارزان‌تر است.
۳. پلن pj6: موسِ حین تایپ سالم بماند (صفر فریز ≥۵۰۰ms میان‌مسیر). playAudio غیرموازی فوری بماند.

---

## ۴. publish + گزارش

بلوک publish استاندارد (تأیید حیاتی `bridge\bridge.py` + صفر فایل .cs در ریلیز).
گزارش فارسی: passed/failed هر گام · وجود Step 28 · عدد `poll round 1` از لاگ · فاصله‌ی run→صدا در 2.amsj · هر تغییر اضافی با فایل و خط.
