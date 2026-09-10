# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۰

- خط کاری: `0.9.66 / PLAN|2`
- مخزن: `pedrampedi81-dotcom/smc`
- شاخه: `feat/portable-plan2-app-0966`
- PR: `#26` — همچنان Draft
- مبنای `main`: `f9f819ba7a8a183f2c7f9040c039e7f502abbe26`؛ هیچ تغییر مستقیمی روی `main` انجام نشده است.

## نتیجه‌های تثبیت‌شده

- runtime/compiler بازیابی‌شده با artifact مرجع بایت‌دقیق است.
- Python gate: `103 passed, 0 failed` (`sim2=21`, `sim3=42`, `compiler=40`).
- Windows app build موفق است.
- `TestRunner`: `745 passed, 0 failed`.
- exporter اکنون header `PLAN|2`، engine `0.9.66` و اکشن‌های portable زیر را تولید می‌کند:
  - `MOVETO`, `WHEEL`, `KEY`, `KDOWN`, `KUP`
  - `WSND`, `TRGSND`, `IFSND`, `IFLUX`, `ELSE`, `ENDIF`
  - `LABEL`, `GOTO`, `RAW`
  - `RPKG`, `PKGITEM`, `ENDPKG`
  - `PGROUP`, `PARITEM`, `ENDPAR`
  - macroهای `runExe`, `openFile`, `playAudio`
  - `INCLUDE`
- `findImage` و typing غیر ASCII/secret/clipboard همچنان صریحاً blocking هستند؛ silent skip وجود ندارد.
- انتشار سه‌فایلی `plan.txt` + `plan_engine.py` + `README-PLAN.md` اتمیک و rollback-safe است.
- گارد CI برای منع `ams_key.json`, `ams_key.h`, کلید خصوصی/token، HEX شخصی/واقعی و backupهای flash/EEPROM اضافه شد.

## موارد باز پیش از تست فیزیکی

1. bundle بازگشتی includeها: parse/compile child `.amsj`، سقف عمق ۴، cycle/missing/duplicate guard و انتشار اتمیک همه‌ی child planها.
2. تبدیل validator از counter به stack نوع‌دار و پوشش duplicate `ELSE` و nesting نامعتبر.
3. تکمیل negative tests برای include، package/group و rollback چندفایلی.
4. همسوسازی نهایی `patch_plan_exporter_ui.py` با migrationهای idempotent.

## baseline سخت‌افزار که نباید تغییر کند

- Pico transport: `0.9.64f`
- Pro Micro: `2.5`
- پذیرش: zero unintended excursions و صفر `BADMOVE`, `PARTIAL WRITE`, `NO-DROP`, `CKSUM`, `NOFRAME`.

## قواعد ثابت

- هرگز selective merge نه؛ `main` فقط از مسیر PR.
- هیچ استپ پشتیبانی‌نشده‌ای silent skip نشود.
- شرط همه‌ی gateها `0 failed` است.
- فایل کلید واقعی، HEX حساس و backup وارد مخزن نشود.
- version bump فقط در PR جدا و پس از پذیرش سخت‌افزاری.
