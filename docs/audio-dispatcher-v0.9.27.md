# v0.9.27 — صدای فوری در Parallel Group (MediaPlayer روی Dispatcher)

**تاریخ:** 2026-09-02 · **پایه:** v0.9.26 · **محرک:** گزارش کاربر — در پلن 2.amsj (تایپ موازی + findImage → playAudio) آهنگ با تاخیر ۵–۱۰ ثانیه پخش شد، با اینکه هیچ Delayای تنظیم نشده بود.

## پلن و مسیر اجرا

پلن: `parallelGroup { typeText … , findImage(region ‏338×108، similarity ‏65٪، timeout ‏80ms، onFound=none، onTimeout=continue، insertIfElse) → child: playAudio(mp3) }`.

بررسی‌شده و سالم:
- نگاشت کمبوی `timeoutUnit` (index ↔ مقدار) در SearchPictureDialog درست است (`ms→0, second→1, minute→2, hour→3` در هر دو جهت) — مقدار `ms` در فایل واقعاً همین بوده، regression ترجمه نیست.
- با timeout=80ms جست‌وجو تقریباً همان poll اول تصمیم می‌گیرد؛ چون صدا پخش شده، تصویر همان ابتدای اجرا پیدا شده → **تاخیر در مسیر vision نبوده**.
- پل میانی: polling تطبیقی روی صفحه‌ی ثابت ۲٫۵–۵ FPS است (تا ~۴۰۰ms) — آن هم به ۵–۱۰s نمی‌رسد.

## ریشه

`MediaPlayer` وابستگی thread-affinity به یک Dispatcherِ pump‌شده دارد. مسیر ترتیبی: `Run()` از روی UI thread شروع می‌شود و `await`ها SynchronizationContextِ WPF را capture می‌کنند → استپ‌های ترتیبی (از جمله playAudio تنها) روی UI thread ادامه می‌یابند → پخش فوری. اما شاخه‌های Parallel Group با `Task.Run` روی thread-pool می‌روند — بدون Dispatcher pump — و در آنجا `Open/Play` گیر می‌کند (شروع پخش ثانیه‌ها طول می‌کشد؛ گزارش کاربر ۵–۱۰s) و `MediaEnded` هرگز fire نمی‌شود (loop شکسته + پلیرهای غیرلوپ خودشان بسته نمی‌شدند و تا پایان run نشت می‌ماندند).

## رفع

- کیس `playAudio` در RunEngine: ساختن/بازکردن/پخش پلیر و اتصال `MediaEnded` همه داخل `Application.Current.Dispatcher.Invoke(...)` — شروع فوری و رویدادها قابل‌اعتماد.
- `StopAllAudio` هم به همان dispatcher مارشال می‌شود (affinity برای Stop/Close).
- بدون تغییر در پروتکل برد؛ بدون تغییر رفتاری در مسیر ترتیبی (قبلاً درست کار می‌کرد).

## تست

گام ۲۷ (۵ assertion، نگهبان فایلی روی RunEngine.cs مانند الگوی گام ۲۵): وجود Dispatcher.Invoke در کیس playAudio · اتصال MediaEnded داخل بلوک dispatcher · مارشال‌شدن StopAllAudio.
