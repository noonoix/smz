# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۱

- خط ریلیز اپ: `0.9.66 / PLAN|2`
- مخزن: `pedrampedi81-dotcom/smc`
- شاخه‌ی ریلیز: `release/app-0.9.66`
- PR #26 با squash در `main` ادغام شد.
- merge commit مبنا: `837188161e5edb441802d9ff0d5ebdff58fb9cf2`.
- Issue #25 با `state_reason=completed` بسته شد.
- head نهایی پیش از merge: `8b4d049406eb7532b2d23fdc993551ba675ae94b`.
- Windows app CI نهایی: run `34574394673` / job `103183453164` — success.

## پذیرش تثبیت‌شده

- hotfix سخت‌افزاری `h6-v2` روی Pico واقعی پذیرفته شد.
- GP4/Num Lock وسط `KTEXT` توقف فوری می‌دهد.
- پایان طبیعی finite plan موتور را به Idle برمی‌گرداند و اجرای بعدی با یک فشار شروع می‌شود.
- لاگ `pico-console-20260911-095058.txt` هیچ `plan: run error` یا `PlanAbort isn't defined` نداشت.
- PONG پذیرفته‌شده: `role=brain+keyboard+light`, `arm=promicro`, `planapi=3`, `engine=split`, `framing=1`, `baud=57600`, `lagmax=2`.
- شمارنده‌های خرابی `cksum=0`, `noframe=0`, `sentjumps=0`, `partial=0` بودند؛ `dropped` coalescing عمدی تحت back-pressure است.
- همه‌ی gateهای نهایی compile، golden، compiler، sim2، sim3، hashes، sensitive-guard و Windows build-test سبز شدند.
- runtime سه‌فایلی در بودجه است: core ≤ 26,000، motion ≤ 15,000 و typing ≤ 5,000 بایت.
- exporter، child planهای بازگشتی و runtime سه‌فایلی را با transaction کامل stage/publish/rollback منتشر می‌کند.

## سیاست نسخه‌ی ریلیز

- نسخه‌ی اپ در این PR از `0.9.65` به `0.9.66` می‌رود.
- Pico firmware bundle عمداً روی baseline پذیرفته‌شده‌ی `0.9.64f` می‌ماند.
- Pro Micro عمداً روی baseline پذیرفته‌شده‌ی `2.5` می‌ماند.
- هیچ فایل کلید واقعی، HEX حساس یا backup وارد مخزن نمی‌شود.

## گیت ادغام PR ریلیز

1. app build بدون خطا.
2. TestRunner با `0 failed`.
3. تمام checkهای PLAN2 و sensitive guard سبز روی head نهایی.
4. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.

## بعد از ریلیز اپ

- در صورت نیاز، candidate artifact رسمی از نام قدیمی `h5` به خط پذیرفته‌شده‌ی `h6` ارتقا داده شود؛ این کار از bump اپ جدا نگه داشته می‌شود.
