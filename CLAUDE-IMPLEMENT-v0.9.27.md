# CLAUDE IMPLEMENT — v0.9.27

**موضوع:** صدای فوری در Parallel Group — MediaPlayer روی UI Dispatcher
**تاریخ:** 2026-09-02 — **پایه:** v0.9.26 (بیلد تأییدشده‌ی تو؛ DLL حاوی بنر v0.9.26 بود)

---

## ۰. قانون طلایی

> **هرگز selective merge نکن.** کل `ams-shell/src/` را پاک کن و نسخه‌ی زیپ را کامل جایگزین کن.
> `tests/TestRunner.cs` و `docs/` را هم جایگزین کن.

---

## ۱. چرا این نسخه

گزارش کاربر (پلن 2.amsj): playAudio داخل Parallel Group با **۵–۱۰ ثانیه تاخیر** شروع شد، بدون هیچ Delay تنظیمی.

ریشه (کد + معماری WPF): استپ‌های ترتیبی روی UI thread ادامه می‌یابند (await، SynchronizationContext را capture می‌کند) ولی شاخه‌های Parallel Group با `Task.Run` روی thread-pool بدون Dispatcher pump می‌روند؛ `MediaPlayer` آنجا گیر می‌کند — شروع دیرهنگام + `MediaEnded` هرگز fire نمی‌شد (loop شکسته، پلیر غیرلوپ نشت).

**تغییرات این درخت (اعمال‌شده — فقط build کن):**
- کیس `playAudio` در `Services/RunEngine.cs`: همه‌ی کارهای پلیر داخل `Application.Current.Dispatcher.Invoke(...)`.
- `StopAllAudio` به همان dispatcher مارشال می‌شود.
- بنر v0.9.27 · `csproj Version` ← 0.9.27 · گام ۲۷ TestRunner (۵ assertion، نگهبان فایلی) · `docs/audio-dispatcher-v0.9.27.md` · ورودی MEMORY.md.
- نکته‌ی مستندشده: `timeoutUnit: ms` در 2.amsj واقعاً ms است (نگاشت کمبو سالم — regression نیست)؛ با timeout=80ms جست‌وجو تقریباً همان poll اول تصمیم می‌گیرد. اگر منظور ۸۰ ثانیه بوده، در دیالوگ واحد را second بگذار.

---

## ۲. بلوک build — اجباری

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.27.txt
python tests\windmouse_check.py
```

---

## ۳. معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۲۷ همه PASS (گام ۲۷: ۵ assertion)
- [ ] بنر: `Classroom Studio v0.9.27 — instant parallel audio …`
- [ ] منوی Insert شامل Parallel Group است

### تست دستی

۱. **پلن 2.amsj** را اجرا کن: به‌محض پیدا شدن تصویر، آهنگ باید **بلافاصله** شروع شود (نه ۵–۱۰s). لاگ سریال را نگه دار: فاصله‌ی زمانی بین «find image: found at …» و شنیده‌شدن صدا باید کمتر از ~۱s باشد.
۲. پلن pj6 را هم یک بار اجرا کن — رفتار موسِ حین تایپ v0.9.26 باید سالم بماند (صفر فریز ≥۵۰۰ms میان‌مسیر).
۳. یک playAudio غیرموازی (تک‌استپ) هم تست کن — باید مثل قبل فوری باشد.

---

## ۴. publish + گزارش

بلوک publish استاندارد (تأیید حیاتی `bridge\bridge.py` + صفر فایل .cs در ریلیز).
گزارش فارسی: passed/failed هر گام · وجود Step 27 · نتیجه‌ی تست دستی 2.amsj (فاصله‌ی found→صدا) · هر تغییر اضافی با فایل و خط.
