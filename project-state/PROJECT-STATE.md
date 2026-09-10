# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۱

- خط کاری: `0.9.66 / PLAN|2`
- مخزن: `pedrampedi81-dotcom/smc`
- شاخه: `feat/portable-plan2-app-0966`
- PR: `#26` — همچنان Draft تا ثبت PONG نهایی و تأیید مشاهده‌ای تایپ/حرکت
- مبنای `main`: `f9f819ba7a8a183f2c7f9040c039e7f502abbe26`؛ هیچ تغییر مستقیمی روی `main` انجام نشده است.
- checkpoint split-runtime سبز: `0df78e3f`.

## نتیجه‌های تثبیت‌شده

- Python gate اصلی: `103 passed, 0 failed` (`sim2=21`, `sim3=42`, `compiler=40`).
- Windows app build: `0 errors`؛ هشدارهای nullable موجود و غیرمسدودکننده‌اند.
- `TestRunner`: `752 passed, 0 failed`.
- engine کامل canonical برابر `50,174 bytes` و SHA-256 صحیح آن `b94b4e8ba3647851814e0a7ea6a1ceb9d92c033a3ad8cc7058a0143853ed3674` است.
- import مستقیم engine کامل روی Pico/CircuitPython 10.3.0 با `memory allocation failed, allocating 3112 bytes` شکست خورد؛ این محدودیت با حذف opcode پنهان نشده است.
- generator قطعی `tools/split_plan_engine.py` همان engine canonical را به runtime سه‌فایلی lazy تبدیل می‌کند:
  - `plan_engine.py`: `24,994 bytes` — `c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac`
  - `plan_motion.py`: `14,028 bytes` — `9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8`
  - `plan_typing.py`: `3,967 bytes` — `1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5`
- differential gate split-runtime برابر `18 passed, 0 failed` است و PLAN|1/2، همه‌ی flow/sound/light/key/raw/package/parallel/beep/includeهای پوشش‌داده‌شده، negative parser cases و lazy import را با canonical مقایسه می‌کند.
- build سخت‌افزاری `pico-light 0.9.64f-plan2h4` روی Pico واقعی `plan: loaded 7 ops` و سپس `plan: rmouse -> (1286,234) 175 pts` ثبت کرد؛ بنابراین core، typing (که قبل از RMOUSE اجرا می‌شود) و motion هر سه بدون MemoryError بارگذاری شدند. در لاگ ۶۰ثانیه‌ای هیچ `MemoryError`، `run error` یا `ack watchdog reset` ثبت نشد.
- exporter اکنون `plan.txt`، child planهای بازگشتی، `plan_engine.py`، `plan_motion.py`، `plan_typing.py` و `README-PLAN.md` را در یک transaction stage/publish/rollback می‌کند.
- هر سه ماژول Python به‌شکل byte-identical داخل `PlanExporter.cs` جاسازی و در TestRunner با goldens تولیدشده مقایسه می‌شوند.
- size budget در CI: core حداکثر 26,000، motion حداکثر 15,000 و typing حداکثر 5,000 بایت.
- `findImage` و typing غیر ASCII/secret/clipboard صریحاً blocking هستند؛ silent skip وجود ندارد.
- `playScript` childهای `.amsj` را بازگشتی با depth cap چهار، cycle/missing/malformed/collision guard و `PlayRepeatMode=once` compile می‌کند.
- گارد CI برای منع `ams_key.json`, `ams_key.h`، کلید خصوصی/token، HEX شخصی/واقعی و backupهای flash/EEPROM فعال و سبز است.

## سیاست bundle

- child plan قدیمی که دیگر در dependency graph نیست خودکار حذف نمی‌شود؛ پاک‌سازی آن باید آگاهانه و دستی انجام شود.
- generator split منبع حقیقت را fork نمی‌کند؛ خروجی سه‌فایلی همیشه از canonical engine بازتولید می‌شود.
- شکست staging/publish باید کل bundle قبلی شامل هر سه ماژول runtime را بازگرداند و `.tmp/.bak` باقی نگذارد.

## مرحله‌ی باز بعدی

1. ثبت PONG نهایی `h4` با `planapi=3|engine=split` و صفر `cksum/noframe/sentjumps/partial`.
2. تأیید مشاهده‌ای اینکه `PLAN2_OK` دقیقاً یک بار تایپ و موس یک بار نرم حرکت کرده است.
3. پس از این پذیرش نهایی، آماده‌سازی PR جدا برای version bump؛ هیچ bump در PR #26 انجام نشود.

## baseline سخت‌افزار که نباید تغییر کند

- Pico transport: `0.9.64f-plan2h4` روی CircuitPython `10.3.0`
- Pro Micro: `2.5`

## قواعد ثابت

- هرگز push مستقیم به `main`؛ فقط branch و PR.
- هیچ استپ پشتیبانی‌نشده‌ای silent skip نشود.
- شرط همه‌ی gateها `0 failed` است.
- فایل کلید واقعی، HEX حساس و backup وارد مخزن نشود.
- version bump فقط در PR جدا و پس از پذیرش سخت‌افزاری.
