# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۱

- خط ریلیز اپ: `0.9.66 / PLAN|2`.
- مخزن: `pedrampedi81-dotcom/smc`.
- PR #26 با squash در `main` ادغام شد: `837188161e5edb441802d9ff0d5ebdff58fb9cf2`.
- PR #27 نسخه‌ی اپ را مستقل به `0.9.66` رساند: `af2a9cdc747443fd8fb3c426df85f683ce4a9b6e`.
- ریلیز رسمی اپ: `ci-31` با `751 passed, 0 failed`.
- `Classroom-Studio-release.zip`: SHA-256 `1C1E9C2B4AF56663C65954AFC131FD44A5FBEE8959D7457762F5FE0ABD0247CB`، اندازه `3262189` بایت.
- PR #28 workflow رسمی candidate را به `h6` ارتقا داد: `c0216f73b6ecd775f05f711a115efccef2c6a118`.
- candidate run `34583319872` / job `103211678767` و sensitive run `34583323201` / job `103211689036` سبز شدند.
- artifact candidate: `Classroom-Studio-PLAN2-h6.zip` + `plan2-h6-sha256.txt` + `ci-test-output.txt`، retention برابر ۱۴ روز.
- Issue #25 با `state_reason=completed` بسته است.

## پذیرش تثبیت‌شده

- hotfix سخت‌افزاری `h6-v2` روی Pico واقعی پذیرفته شد.
- GP4/Num Lock وسط `KTEXT` توقف فوری می‌دهد.
- پایان طبیعی finite plan موتور را به Idle برمی‌گرداند و اجرای بعدی با یک فشار شروع می‌شود.
- لاگ `pico-console-20260911-095058.txt` هیچ `plan: run error` یا `PlanAbort isn't defined` نداشت.
- PONG پذیرفته‌شده: `role=brain+keyboard+light`, `arm=promicro`, `planapi=3`, `engine=split`, `framing=1`, `baud=57600`, `lagmax=2`.
- شمارنده‌های خرابی `cksum=0`, `noframe=0`, `sentjumps=0`, `partial=0` بودند؛ `dropped` coalescing عمدی تحت back-pressure است.
- همه‌ی gateهای compile، golden، compiler، sim2، sim3، hashes، sensitive-guard و Windows build-test سبز شدند.
- runtime سه‌فایلی در بودجه است: core ≤ 26,000، motion ≤ 15,000 و typing ≤ 5,000 بایت.
- exporter، child planهای بازگشتی و runtime سه‌فایلی را با transaction کامل stage/publish/rollback منتشر می‌کند.

## قرارداد نسخه‌ی نهایی

- Classroom Studio: `0.9.66`.
- Pico firmware bundle: baseline پذیرفته‌شده‌ی `0.9.64f`.
- Pro Micro: baseline پذیرفته‌شده‌ی `2.5`.
- PLAN format: `PLAN|2`، engine line: `0.9.66`.
- هیچ فایل کلید واقعی، HEX حساس یا backup وارد مخزن نشده است.

## گیت‌های تثبیت‌شده

1. app build بدون خطا.
2. TestRunner با `0 failed`.
3. تمام checkهای PLAN2 و sensitive guard سبز روی head نهایی.
4. marker مربوط به `PLAN2_H6_CONTROL_FIX` و رفتارهای پایان طبیعی و توقف‌پذیری تایپ بررسی می‌شوند.
5. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.
