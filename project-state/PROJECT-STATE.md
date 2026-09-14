# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۴

- مخزن فعال: `kirobesaban/smc-1`.
- شاخه‌ی پایدار: `main`.
- head پایدار: `a1aa9e552cd52ffcf676b596199db81efac9c51f`.
- آخرین Release معتبر: `ci-115` با `770 passed, 0 failed`.
- SHA-256 فایل `Classroom-Studio-release.zip`: `E8BBC4FFF05118EB9F9A7EA0FE6AA38F8661917DE8C9CFEB6BCDBDE066CFDF2E`.
- خط ریلیز اپ: `0.9.67 / PLAN|2`.
- شاخه‌ی ارتقای جاری: `feature/light-telemetry-protocol`.

## معماری تثبیت‌شده

- Classroom Studio محیط ساخت، تنظیم، کالیبراسیون، تست و Export است.
- Pico مغز اجرایی مستقل، مجری Keyboard، سنسور نور BH1750 و موتور پرتابل است.
- Pro Micro بازوی Mouse و Sound Sensor است و از طریق UART با Pico کار می‌کند.
- BH1750 روی Pico با `SDA=GP20`، `SCL=GP21` و آدرس `0x23` است.
- قراردادهای اجرایی `WLUX` و `TRGLUX` و قرارداد کالیبراسیون `LCAL` حفظ می‌شوند.

## ارتقای جاری: Status و Live Watch نور

فاز صفر در `ams-shell/src/Ams.UI/docs/light-telemetry-phase-zero.md` ثبت شده است.

ترتیب اجرا:

1. فرمان فقط‌خواندنی `LUX?` و تست Firmware، بدون تغییر XAML.
2. API typed در Bridge و Watch Service بدون overlap.
3. تب مستقل Status با Lux زنده، health، نمودار و آمار.
4. Light State Profile و classifier با stable duration، hysteresis و overlap guard.
5. تست نرم‌افزاری و سخت‌افزاری BH1750.
6. QA بصری، CI با `0 failed` و Release.

## مرز ایمنی

- Live Watch کاملاً مشاهده‌ای و بدون Side Effect است.
- Watch حق اجرای Macro، فشردن کلید، BEEP یا overwrite کالیبراسیون را ندارد.
- Light State و confidence در مراحل اولیه فقط نمایشی‌اند.
- گیت اجرایی Launch/Auto Resume تا قرارداد ایمنی جداگانه فعال نمی‌شود.

## گیت‌های دائمی

1. build اپ بدون خطا.
2. TestRunner با `0 failed`.
3. parity خروجی عادی و AutoCycle.
4. گیت sensitive guard سبز.
5. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.
6. تغییر UI فقط بعد از آماده‌شدن Protocol و Bridge typed.
