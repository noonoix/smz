# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۰

- خط کاری: `0.9.66 / PLAN|2`
- مخزن: `pedrampedi81-dotcom/smc`
- شاخه: `feat/portable-plan2-app-0966`
- PR: `#26` — همچنان Draft تا پذیرش سخت‌افزاری
- مبنای `main`: `f9f819ba7a8a183f2c7f9040c039e7f502abbe26`؛ هیچ تغییر مستقیمی روی `main` انجام نشده است.
- checkpoint نرم‌افزاری سبز: `6951a299`؛ پاک‌سازی workflow/Bootstrap تا `2c40f9fb` ادامه یافته است.

## نتیجه‌های تثبیت‌شده

- runtime/compiler بازیابی‌شده با artifact مرجع بایت‌دقیق است.
- Python gate: `103 passed, 0 failed` (`sim2=21`, `sim3=42`, `compiler=40`).
- Windows app build موفق است: `0 errors` (هشدارهای nullable موجود و غیرمسدودکننده‌اند).
- `TestRunner`: `751 passed, 0 failed`.
- engine جاسازی‌شده با `portable/plan3/CIRCUITPY/plan_engine.py` بایت‌دقیق است؛ SHA-256 برابر `b94b4e8ba3647851814e7ea6a1ceb9d92c033a3ad8cc7058a0143853ed3674`.
- exporter header `PLAN|2`، engine `0.9.66` و اکشن‌های portable زیر را تولید می‌کند:
  - `MOVETO`, `WHEEL`, `KEY`, `KDOWN`, `KUP`
  - `WSND`, `TRGSND`, `IFSND`, `IFLUX`, `ELSE`, `ENDIF`
  - `LABEL`, `GOTO`, `RAW`
  - `RPKG`, `PKGITEM`, `ENDPKG`
  - `PGROUP`, `PARITEM`, `ENDPAR`
  - macroهای `runExe`, `openFile`, `playAudio`
  - `INCLUDE`
- `findImage` و typing غیر ASCII/secret/clipboard صریحاً blocking هستند؛ silent skip وجود ندارد.
- `playScript` اکنون childهای `.amsj` را به‌شکل بازگشتی compile می‌کند:
  - مسیر child نسبت به فایل parent resolve می‌شود.
  - root در depth صفر است و حداکثر چهار سطح child مجاز است.
  - cycle، فایل مفقود/خراب، collision نام خروجی و nesting نامعتبر blocking هستند.
  - یک source تکراری فقط یک‌بار emit می‌شود و childها با `PlayRepeatMode=once` compile می‌شوند.
- انتشار bundle شامل `plan.txt`، همه‌ی child planهای `*.txt`، `plan_engine.py` و `README-PLAN.md` است؛ کل انتشار atomically stage/publish/rollback می‌شود و `.tmp/.bak` باقی نمی‌ماند.
- validator از counterهای مستقل به stack نوع‌دار برای `LOOP`, `IF`, `RPKG`, `PGROUP` تبدیل شده و cross-close، duplicate `ELSE` و item/branch خالی را رد می‌کند.
- UI مسیر کامل فایل جاری را فقط برای resolve داخلی می‌فرستد؛ header و README فقط basename را نمایش می‌دهند و مسیر خصوصی سیستم افشا نمی‌شود.
- migrationهای source/test idempotent به workflow ویندوز متصل‌اند و generated exporter/TestRunner از sourceهای canonical همگام می‌شوند.
- گارد CI برای منع `ams_key.json`, `ams_key.h`، کلید خصوصی/token، HEX شخصی/واقعی و backupهای flash/EEPROM فعال و سبز است.

## سیاست bundle

- child plan قدیمی که دیگر در dependency graph نیست خودکار حذف نمی‌شود؛ حذف خودکار می‌تواند فایل unrelated روی CIRCUITPY را از بین ببرد. پاک‌سازی فایل‌های قدیمی باید آگاهانه و دستی انجام شود.

## مرحله‌ی باز بعدی

1. تست فیزیکی end-to-end روی baseline ثابت.
2. بررسی zero unintended excursions و صفر `BADMOVE`, `PARTIAL WRITE`, `NO-DROP`, `CKSUM`, `NOFRAME`.
3. در صورت پذیرش سخت‌افزاری، آماده‌سازی PR جدا برای version bump؛ PR فعلی تا آن زمان Draft می‌ماند.

## baseline سخت‌افزار که نباید تغییر کند

- Pico transport: `0.9.64f`
- Pro Micro: `2.5`

## قواعد ثابت

- هرگز selective merge نه؛ `main` فقط از مسیر PR.
- هیچ استپ پشتیبانی‌نشده‌ای silent skip نشود.
- شرط همه‌ی gateها `0 failed` است.
- فایل کلید واقعی، HEX حساس و backup وارد مخزن نشود.
- version bump فقط در PR جدا و پس از پذیرش سخت‌افزاری.
