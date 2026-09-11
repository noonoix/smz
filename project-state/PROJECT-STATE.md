# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۱

- خط ریلیز اپ: `0.9.67 / PLAN|2`.
- مخزن: `pedrampedi81-dotcom/smc`.
- PR #30 با squash در `main` ادغام شد: `042888c63070ef7140cf3bd0ce8d1f92519e03d0`.
- CI اصلی پس از merge: ریلیز `ci-33` با `752 passed, 0 failed`.
- `Classroom-Studio-release.zip`: SHA-256 `80BEEA10705C3E9EB68E8DCE27CCB5830D4907A88E933B18859206C9E38EEB32`، اندازه `3287332` بایت.
- شاخه‌ی bump مستقل: `release/app-0.9.67`.

## پذیرش تثبیت‌شده

- AutoCycle روی سخت‌افزار واقعی پاس شد: Restart Windows، تشخیص `HOSTUSB DOWN → UP` و Auto Resume بدون فشار GP4.
- نشانگر تشخیصی ۳۰ثانیه‌ای `AUTO_RESUME_OK` پس از بوت در Notepad تایپ شد.
- Pro Micro firmware پذیرفته‌شده `2.6.1` است و وضعیت USB/HID را هر دو ثانیه بازاعلام می‌کند.
- فشار اول GP4، debounce 300ms و نگاشت عمومی Shift/Ctrl/Alt روی سخت‌افزار تأیید شدند.
- Restart blocker با ترتیب `ShiftDown → TabDown → TabUp → ShiftUp → Enter` پذیرفته شد.
- Firmware پذیرفته‌شده‌ی h6 با manifest پانزده‌ویرایشی و parity برابر `25 passed, 0 failed` به Exporter متصل است.
- گیت‌های `autocycle / portable contracts`، `autocycle / Windows app build-test`، شش گیت PLAN2 و `security / sensitive-guard` سبز هستند.

## قرارداد نسخه‌ی ریلیز

- Classroom Studio: `0.9.67`.
- Pico firmware bundle: baseline پذیرفته‌شده‌ی `0.9.64f` با patch AutoCycle h6.
- Pro Micro: firmware پذیرفته‌شده‌ی `2.6.1`.
- PLAN format: `PLAN|2`، engine line: `0.9.66`.
- بازر از پذیرش این مرحله خارج و به نوبت بعد موکول شده است.
- هیچ فایل کلید واقعی، HEX حساس یا backup وارد مخزن نشده است.

## گیت‌های PR ریلیز

1. app build بدون خطا.
2. TestRunner با `0 failed`.
3. تمام checkهای AutoCycle، PLAN2 و sensitive guard سبز.
4. پین اپ فقط `0.9.67` و پین bundle فقط خانواده‌ی `0.9.64f` باشد.
5. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.
