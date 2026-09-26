# Classroom Studio — Current Hardware Changelog

این سند مرجع سریع وضعیت شاخهٔ فعال `fix/portable-relative-mouse` است. ترتیب ورودی‌ها معکوس زمانی است؛ جدیدترین Build همیشه بالاتر قرار می‌گیرد.

## وضعیت فعلی در یک نگاه

- **آخرین Build دارای تست سخت‌افزاری:** Build 50
- **وضعیت عملکرد A و B:** هر دو موفق؛ Route کامل شد و `MemoryError` رخ نداد.
- **وضعیت کیفیت حرکت:** B فعلاً برندهٔ روشن است؛ صدک 95 فاصله‌ها از 53ms در A به 15ms در B رسید.
- **معماری:** Pico مسئول Keyboard/Guard/Route، و Pro Micro مسئول Mouse HID و Sound است.
- **Golden 100:** جدا و بدون تغییر باقی مانده است.

| Build | نتیجهٔ سخت‌افزاری | مسئله/تغییر اصلی | وضعیت |
| --- | --- | --- | --- |
| 50 | Route تست B کامل شد | Changelog اجباری؛ همان Runtime Build 49 | B فعلاً بهترین گزینه |
| 49 | Route تست A کامل شد | Runner سبک RMOUSE بدون Executor کامل | Functional pass؛ کیفیت حرکت در حال تیون |
| 48 | Import و Parse موفق؛ اجرا شکست خورد | Lazy import Parser/Executor | Superseded by 49 |
| 47 | تست A در Import شکست خورد | Fishing timeout + cadence 128-point | Superseded by 48/49 |
| 46 | Login RMOUSE و Stop تأیید شدند | Streaming RMOUSE عادی | Verified foundation |
| 45 | بازیابی Heap و حذف SCAL وسط حرکت | Stop cleanup | Verified foundation |
| 43 | Pause release، SCAL BUSY و sampled speed | Timing/UART fixes | Superseded |
| 41 | Parallel memory و پروفایل‌های نور | Streaming parallel RMOUSE | Superseded |
| 40 | Retry کالیبراسیون overlap | Calibration UX | Verified |
| 39 | Facade صحیح در Export پروژهٔ جاری | Export ordering | Verified foundation |
| 38 | Split executor اولیه | کاهش فشار Import | Superseded by 39 |

## Build {{BUILD_NUMBER}} — ثبت نتیجهٔ سخت‌افزاری B

**Previous build:** 50  
**Status:** CI candidate; Build 50 hardware result B recorded  
**Commit:** `{{COMMIT_SHA}}`

### Problem observed

تست A از نظر حافظه موفق بود، اما Record آن 862 فاصلهٔ حداقل 40ms و صدک 95 برابر 53ms داشت؛ بنابراین حرکت از نظر زمانی هنوز نرم نبود.

### Root cause

تنظیم A با `mt=600,600` در ثبت واقعی تعداد زیادی وقفهٔ حدود 52–53ms نشان داد. برای تشخیص اینکه مشکل از Cadence انتخابی است، تست B با زمان حرکت طولانی‌تر و Curve محدود لازم بود.

### Change

- کد Runtime تغییر نکرد.
- نتیجهٔ تست B با `curve=0..8` و `mt=900..1400` در Changelog ثبت شد.
- Bundle ارسالی B بررسی شد و هر 25 Hash در Manifest معتبر بود.
- B به‌عنوان گزینهٔ برتر فعلی برای ادامهٔ مقایسه علامت‌گذاری شد.

### Validation

- لاگ Build 50: پیش از Route مقدار 74,080، پس از Import مقدار 68,896 و پس از Parse مقدار 68,512 بایت آزاد بود.
- Route `desktop_steps.txt` تا `ROUTE/complete` اجرا شد و `MemoryError` رخ نداد.
- Record B: 2,342 موقعیت، 2,341 Segment و 28,863ms زمان ثبت‌شده.
- گام میانه 2.24px، صدک 95 و بیشینه هر دو 2.83px بودند؛ سقف Micro-step حفظ شد.
- فاصلهٔ زمانی میانه 13ms، صدک 80 برابر 14ms و صدک 95 برابر 15ms بود.
- فقط 13 فاصلهٔ حداقل 40ms ثبت شد؛ نسبت به 862 مورد A حدود 98.5٪ کاهش داشت و تقریباً به مکث‌های عمدی Route محدود شد.

### Next test

پروژهٔ C را با Build 50 اجرا و Record آن را ثبت کنید. B معیار فعلی است: p95 فاصله 15ms، فقط 13 فاصلهٔ حداقل 40ms، Micro-step حداکثر 2.83px و اجرای کامل بدون `MemoryError`.

## Build 50 — Changelog اجباری و تأیید سخت‌افزاری A

**Previous build:** 49  
**Status:** CI passed; A hardware result recorded  
**Commit:** [`535cc4cf`](https://github.com/noonoix/smz/commit/535cc4cf77238b357c8cfcfe31ff3788caaf17e8)  
**Release:** [classroom-current-50](https://github.com/noonoix/smz/releases/tag/classroom-current-50)  
**SHA256:** `1e6d2fe654a7020701b26470d5348eae9c45cb5b1dd8f9399ec7616962169cf4`

### Problem observed

اطلاعات علت شکست و اصلاح هر Build در PRها و صفحهٔ داخلی پراکنده بود و متن Release عمومی و تکراری بود.

### Root cause

Workflow انتشار متن ثابت داشت و تغییر Build بدون ورودی Changelog قابل انتشار بود.

### Change

Changelog تجمعی، لینک README، کنترل اجباری Workflow و Release notes تولیدشده از جدیدترین ورودی اضافه شدند.

### Validation

Build 50 نخستین Release با متن واقعی Changelog بود. نتیجهٔ سخت‌افزاری A نیز بدون `MemoryError` تا `ROUTE/complete` رسید.

### Next test

B، C و D برای انتخاب Tempo و Curve مناسب مقایسه شوند.

## Build 49 — Runner سبک RMOUSE

**Previous build:** 48  
**Status:** Hardware functional pass; motion quality pending  
**PR/Commit:** [#16](https://github.com/noonoix/smz/pull/16) / [`2b1919dd`](https://github.com/noonoix/smz/commit/2b1919dda4082d89531723cff82876ba97a69437)  
**Release:** [classroom-current-49](https://github.com/noonoix/smz/releases/tag/classroom-current-49)  
**SHA256:** `2dc6f75b1c84eafd8ebcccb3ba67c99a8d9a222aacb159533879d3f1b23a56a8`

### Problem observed

Build 48 Parser را با حاشیهٔ خوب Load می‌کرد، اما `run_plan` برای Route سادهٔ A موتور کامل 19.9KB را Import می‌کرد و تخصیص 1,016 بایت شکست می‌خورد. اجرای دوم پس از Fragmentation در تخصیص 776 بایت شکست خورد.

### Root cause

Route سادهٔ `RMOUSE + LOOP + DELAY` بی‌دلیل هزینهٔ Import ماژول‌های Human، Parallel و Executor کامل را می‌پرداخت.

### Change

Runner سبک فقط برای Relative Native و مجموعهٔ محدود `PLAN/SCREEN/SPEED/DELAY/LOOP/LOOPTIME/ENDLOOP/RMOUSE` اضافه شد. Routeهای پیچیده همچنان به موتور کامل می‌روند؛ Fishing و Parallel تغییر نکردند.

### Validation

خروجی Runner سبک و موتور کامل روی 100 Seed برابر بود؛ RMOUSE روی 200 Seed و Parallel روی 17 سناریو موفق شد. تست واقعی A به `ROUTE/complete` رسید.

### Next test

B/C/D برای انتخاب Tempo و Curve مناسب مقایسه شوند.

## Build 48 — جداسازی Import Parser از Executor

**Previous build:** 47  
**Status:** Partial hardware pass; superseded by 49  
**PR/Commit:** [#15](https://github.com/noonoix/smz/pull/15) / [`3f2a03d7`](https://github.com/noonoix/smz/commit/3f2a03d77281825b093ac132074238bad437b5eb)  
**Release:** [classroom-current-48](https://github.com/noonoix/smz/releases/tag/classroom-current-48)  
**SHA256:** `048044fdf71dfc8fda0469508e15e59287e30f873e9d09c7e0f9a211fd334bec`

### Problem observed

Build 47 هنگام Import هم‌زمان Parser، Human و Executor با تخصیص 2,344 بایت شکست خورد.

### Root cause

Facade هنگام درخواست اولیهٔ `parse_plan` همهٔ ماژول‌های اجرایی را نیز Import می‌کرد.

### Change

Parser زودهنگام و Executor داخل `run_plan` به‌صورت Lazy بارگذاری شد.

### Validation

در سخت‌افزار Import با 71,328 بایت و Parse با 70,960 بایت آزاد کامل شد؛ شکست بعدی فقط Import Executor بود و در Build 49 رفع شد.

## Build 47 — Fishing timeout و Cadence موس

**Previous build:** 46  
**Status:** Fishing semantics fixed; A import failed  
**PR/Commit:** [#14](https://github.com/noonoix/smz/pull/14) / [`d324a5b8`](https://github.com/noonoix/smz/commit/d324a5b8afa61db8114f3c1e83a2fcd94980e10d)  
**Release:** [classroom-current-47](https://github.com/noonoix/smz/releases/tag/classroom-current-47)  
**SHA256:** `efe23c93ff45575b485ec0bdd1fda60f40f3c617f6c7194f2bb4111b4c6483f2`

### Problem observed

پس از Timeout صدای ماهیگیری، شاخهٔ Sound پایان می‌یافت اما Loop بی‌نهایت موس فعال می‌ماند؛ در نتیجه قلاب مجدد اجرا نمی‌شد. حرکت نیز بین نقاط Pico وقفه‌های حدود 40–55ms داشت.

### Root cause

Timeout کل Parallel Group را لغو نمی‌کرد و مسیر Streaming فقط تا 32 نقطهٔ زمانی داشت.

### Change

Timeout کل گروه را لغو می‌کند، واکنش `F` را رد می‌کند و به Loop بیرونی برمی‌گردد. Cadence هدف 8ms و سقف Streaming برابر 128 نقطه شد.

### Validation

تست‌های Parallel 17/17 و Relative RMOUSE روی 200 Seed موفق شدند. تست A بعداً فشار Import مستقل را آشکار کرد.

## Build 46 — Streaming RMOUSE عادی Login/DC

**Previous build:** 45  
**Status:** Hardware verified  
**PR/Commit:** [#13](https://github.com/noonoix/smz/pull/13) / [`946f736b`](https://github.com/noonoix/smz/commit/946f736bad76b65250a31faa33b8d299cbeef5cc)  
**Release:** [classroom-current-46](https://github.com/noonoix/smz/releases/tag/classroom-current-46)  
**SHA256:** `04febadd9d9b0d8e387f71d3b085e7b2ac81cbfd1f5f609231b055f50c84d812`

### Problem observed

Login/DC پس از Parse و `SCREEN` در نخستین RMOUSE با تخصیص 2,048 بایت شکست می‌خورد.

### Root cause

RMOUSE غیرموازی هنوز چند لیست متراکم WindMouse را در RAM می‌ساخت؛ اصلاح Streaming فقط در Parallel فعال بود.

### Change

RMOUSE نسبی عادی نیز Streaming شد و متن Route پیش از نخستین حرکت آزاد شد.

### Validation

تست سخت‌افزاری Login/DC با 51,776 بایت و Game با 49,120 بایت پس از Parse موفق شد؛ Stop به‌صورت `ROUTE/aborted` ثبت شد.

## Build 45 — حذف SCAL وسط حرکت و بازیابی Heap

**Status:** Verified foundation  
**Commits:** [`1bc0c5c7`](https://github.com/noonoix/smz/commit/1bc0c5c78e2c73fa7e255963955066fdb2d2da69)، [`894bad14`](https://github.com/noonoix/smz/commit/894bad14738601b87dbf7ff91b5f01096c55ab9d)  
**Release:** [classroom-current-45](https://github.com/noonoix/smz/releases/tag/classroom-current-45)  
**SHA256:** `59e5056286be6000c24695e013974d023c81d68f975efb059ae514d3d9915eaf`

- Poll صوتی `SCAL|10` هنگام Stream فعال موس اجرا نمی‌شود و به نقاط توقف عمدی منتقل شد.
- `PlanAbort` ناشی از Stop دیگر Guard Failure نیست.
- ماژول‌های Plan پس از Route از Cache خارج می‌شوند تا Start بعدی Heap تازه داشته باشد.

## Build 43 — Pause، SCAL BUSY و سرعت Sample

**Status:** Superseded but retained behavior  
**Commits:** [`58fff88d`](https://github.com/noonoix/smz/commit/58fff88dcf9e0a3c33a3addafca161590a46a883)، [`55d4b081`](https://github.com/noonoix/smz/commit/55d4b0818e64b259e7a2c6582b1dfb9f871fc78a)  
**Release:** [classroom-current-43](https://github.com/noonoix/smz/releases/tag/classroom-current-43)  
**SHA256:** `fbde9312b55de60e69324d1dedc9235ec2c2a7ef560940b97b2c107054a1b82b`

- Pause فوراً `keyboard.release_all()` می‌کند.
- پیش از SCAL صف ARM Flush و BUSY گذرا Retry می‌شود.
- Hand Sample منبع Tempo است و هزینهٔ Micro-step دوباره به زمان حرکت افزوده نمی‌شود.

## Build 41 — Parallel streaming و پروفایل نور

**Status:** Superseded  
**Commit:** [`13277a93`](https://github.com/noonoix/smz/commit/13277a935b3f0520c045fa12cb11fd658ee9bf01)  
**Release:** [classroom-current-41](https://github.com/noonoix/smz/releases/tag/classroom-current-41)  
**SHA256:** `0b0677c9a3c1d045f1aacf299be7360fce7042be69e3e83765c7e468afb999d4`

Parallel RMOUSE از لیست متراکم به Curve Streaming منتقل شد و Parsing پاسخ SCAL کم‌Allocation شد. پروفایل‌های Character Dashboard و Game تثبیت شدند.

## Build 40 — Retry کالیبراسیون پس از Overlap

**Status:** Verified  
**Commit:** [`034e46c8`](https://github.com/noonoix/smz/commit/034e46c8a175c15804c4b2861c722d86063ff0ec)  
**Release:** [classroom-current-40](https://github.com/noonoix/smz/releases/tag/classroom-current-40)  
**SHA256:** `a281f4ad03432f5828345ac5197581adc0930d3cf40d96a36b9446246d86bf64`

پس از رد `CAL|OVERLAP`، زرد نمونه‌گیری تازه را آغاز می‌کند؛ آبی کوتاه Stage نامعتبر را رد نمی‌کند و آبی بلند خارج می‌شود. بازخورد صوتی خطا اضافه شد.

## Build 39 — حفظ Facade مدرن در Export پروژهٔ جاری

**Status:** Verified foundation  
**Commit:** [`7efce2da`](https://github.com/noonoix/smz/commit/7efce2da545648f17a102afd5a148f596c92bfa6)  
**Release:** [classroom-current-39](https://github.com/noonoix/smz/releases/tag/classroom-current-39)  
**SHA256:** `ca5ea9c0175ec76bc1271567f0c9c83caf382aede25d3ee885c77a0eb6221369`

Exporter Legacy پس از تولید Routeها، Facade مدرن را با Engine یکپارچهٔ 30KB جایگزین می‌کرد. ترتیب Export اصلاح و Hash نهایی Manifest دوباره ساخته شد.

## Build 38 — Split اولیهٔ Executor و Parallel

**Status:** Superseded by 39  
**Commits:** [`c1ad2385`](https://github.com/noonoix/smz/commit/c1ad2385333f0a46f2c945620e5a865bc6f8630d)، [`dfe4102a`](https://github.com/noonoix/smz/commit/dfe4102a421807087a00910a6918c2a2bbe73964)، [`eaa65f96`](https://github.com/noonoix/smz/commit/eaa65f969fd2abd430c04846e1f2ba1ac18fffec)  
**Release:** [classroom-current-38](https://github.com/noonoix/smz/releases/tag/classroom-current-38)  
**SHA256:** `af7af2a700d17be4254248642ddc883283e105053ce1fd2b28b634f1eafd64b7`

Scheduler Parallel از Executor جدا و Lazy-load شد. Export اشتباه Facade در Build 39 اصلاح شد.

## قانون به‌روزرسانی

برای هر تغییر Build‌ساز:

1. بخش `Build {{BUILD_NUMBER}}` فعلی را با شمارهٔ واقعی Build قبلی تثبیت کنید.
2. یک بخش جدید `Build {{BUILD_NUMBER}}` در بالای تاریخچه اضافه کنید.
3. Problem، Root cause، Change، Validation و Next test را تکمیل کنید.
4. وضعیت Hardware را از CI جدا نگه دارید؛ CI سبز به‌تنهایی به معنی تأیید سخت‌افزاری نیست.
5. Workflow بدون تغییر همین فایل اجازهٔ انتشار Build جدید را نمی‌دهد.
