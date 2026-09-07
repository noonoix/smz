# CLAUDE IMPLEMENT — v0.9.26

**موضوع:** موس روان حین تایپ در Parallel Group (مهار با سقف + استراحت‌های کم‌تعداد و کوتاه)
**تاریخ:** 2026-09-02 — **پایه:** v0.9.25 (بیلد تأییدشده‌ی تو، ۲۹۱ تست پاس)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن.

---

## ۱. چرا این نسخه

گزارش کاربر: در اجرای موازی، وقتی تایپ شروع می‌شود موس تکه‌تکه و با قطع‌ووصل حرکت می‌کند.

شواهد (رکورد ۷۲٫۶ ثانیه‌ای اپ با پلن pj6 + رکورد متراکم ۲۰٫۲ ثانیه‌ای دست کاربر):
- اپ: ۷۷ مکث ≥۱۰۰ms حین تایپ؛ ۱۱ فریز ≥۵۰۰ms؛ دو فریز میان‌مسیر **۱۲٫۴s و ۱۱٫۰s** در حالی که تایپ با کادنس عادی جریان داشت → کانال سریال سالم؛ شاخه‌ی موس پارک بود.
- دست: حین تایپ p90 گپ موس ۶ms، حداکثر ۳۵۱ms، **صفر** فریز ≥۵۰۰ms.

ریشه: ۱) دوبرابرشدن بدون سقفِ تاخیر نقاط مسیر (`SuppressedMouseDelayMs`) — با `moveTimeMax` تا ۷۰۰۰ms، تاخیرهای دمِ مسیر ثانیه‌ای دوبرابر و روی نقاط زیرپیکسل پارک نامرئی چندثانیه‌ای می‌ساختند. ۲) استراحت هر ۲–۶ ضربه (تا ۱۲۰۰ms) که به‌خاطر پنجره‌ی ۹۰۰msی `IsTypingActive` در طول burst پیوسته پشت‌سرهم می‌افتاد.

**تغییرات این درخت (همه اعمال‌شده — فقط build کن):**
- `RunEngine.SuppressedMouseDelayMs` — حالا با سقف `SuppressedMouseDelayCapMs = 140`.
- `MaybeTypingRestAsync` — کادنس هر ۱۰–۲۴ ضربه؛ طول ۹۰–۳۰۰ms (۱۰٪: ۳۵۰–۷۰۰ms)؛ منطق خالص در `NextTypingRestEveryKeys`/`TypingRestMs` برای تست.
- بنر MainViewModel ← v0.9.26 · `csproj Version` ← 0.9.26 · گام ۲۶ TestRunner (۷ assertion) · `docs/mouse-typing-glide-v0.9.26.md` · ورودی MEMORY.md.
- گام ۲۳ دست‌نخورده — assertهایش (۸→۱۶، ۰→۱) زیر سقف معتبر می‌مانند.

---

## ۲. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.26.txt
python tests\windmouse_check.py
```

---

## ۳. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۲۶ همه PASS (گام ۲۶: ۷ assertion)
- [ ] بنر: `Classroom Studio v0.9.26 — smooth mouse glide while typing …`
- [ ] منوی Insert شامل Parallel Group است

### تست دستی — همان پلن pj6

۱. همان پلن «move mouse in pj6.amsj» (تایپ + موس تصادفی موازی) را اجرا کن.
۲. حین تایپ، موس باید **پیوسته** بخزد — بدون توقف‌های چندثانیه‌ای. مکث‌های لحظه‌ای کوتاه (زیر حدود ۱ ثانیه) طبیعی و انسانی‌اند.
۳. رکورد بگیر و با رکورد قبلی بسنج: هدف = **صفر فریز ≥۵۰۰ms میان‌مسیر** حین تایپ؛ مکث‌های ≥۱۰۰ms نادر (تقریباً هر ۱۰–۲۴ ضربه یک بار).
۴. رفتار غیرموازی (حرکت موس تک‌استپ) نباید تغییر کرده باشد — send_path دست‌نخورده است.

---

## ۴. publish + گزارش

بلوک publish استاندارد (تأیید حیاتی `bridge\bridge.py` در خروجی + صفر فایل .cs در ریلیز).
گزارش: passed/failed · وجود Step 26 · مقایسه‌ی رکورد قبل/بعد (بزرگ‌ترین فریز حین تایپ، تعداد مکث ≥۱۰۰ms حین تایپ) · هر تغییر اضافی با فایل و خط.
