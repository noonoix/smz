# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۵

- مخزن فعال: `kirobesaban/smc-1`.
- شاخه‌ی پایدار: `main`.
- head پایدار پس از ادغام فازهای ۱ تا ۳: `0807f221cdc14c720f3fe2bf9b601f3d0a005c33`.
- PRهای `#155`، `#156` و `#157` به‌ترتیب merge شده‌اند.
- شاخه‌ی جاری: `feature/light-state-profiles`.
- PR جاری: `#158`، مستقیماً روی `main`، Ready for review و mergeable.
- head فاز ۴: `088d452682a2454c3e42162ee0e38a7661b9492b`.
- چهار gate نهایی سبزند: portable contracts، Windows build/TestRunner، sensitive guard و downloadable package.
- Release تست نهایی: `light-state-test-269`.
- SHA-256 بسته: `7D79EE7CFADB8DF0431EE4D877B9A23389231305935A698D23579236A7AFFA71`.
- خط ریلیز اپ: `0.9.67 / PLAN|2`.

## معماری تثبیت‌شده

- Classroom Studio محیط ساخت، تنظیم، کالیبراسیون، تست و Export است.
- Pico مغز اجرایی مستقل، مجری Keyboard، سنسور BH1750 و موتور پرتابل است.
- Pro Micro بازوی Mouse و Sound Sensor است و از طریق UART با Pico کار می‌کند.
- BH1750 روی Pico با `SDA=GP20`، `SCL=GP21` و آدرس `0x23` است.
- قراردادهای `LUX?`، `WLUX`، `TRGLUX` و `LCAL` حفظ شده‌اند.

## نتیجه‌ی فازهای Light Telemetry

1. پروتکل فقط‌خواندنی `LUX?` و تست Firmware — کامل و merge شده.
2. Bridge typed و Watch Service بدون overlap — کامل و merge شده.
3. تب مستقل Status با Lux زنده، health، نمودار و آمار — کامل و merge شده.
4. Light State Profiles، classifier، persistence و calibration — کامل، کالیبره و آمادهٔ merge.

## Bridge correlation

Firmware برای درخواست `LUX?` پاسخ `OK|LUX|...` یا خطای `ERR|...|LUX` می‌دهد. بستهٔ اجرایی از entry point سازگار `light_state_bridge.py` استفاده می‌کند که:

- alias پاسخ `LUX? → LUX` را اعمال می‌کند؛
- رویدادهای `EVT|...` را از reply جدا نگه می‌دارد؛
- پاسخ‌های stale مربوط به فرمان‌های دیگر را رد می‌کند؛
- مسیرهای قدیمی Bridge را بدون refactor گسترده حفظ می‌کند.

این مسیر روی Windows و سخت‌افزار واقعی تأیید شده است.

## نتیجه‌ی QA سخت‌افزاری فاز ۴

- اتصال خودکار Pico روی `COM5` با Firmware `pico-light 0.9.64h` موفق بود.
- دریافت پیوستهٔ `OK|LUX` و عبور `EVT|HOSTUSB|UP` بدون mispair تأیید شد.
- نمودار، Min، Max، Average، Spread، Stop و stale state تأیید شدند.
- UI در RTL و عرض کم، و عملیات Apply، Reset، Save و persistence پس از restart تأیید شدند.
- ورودی منفی، `NaN` و فیلد خالی رد شدند.
- تشخیص و گذار هر شش وضعیت بدون Ambiguous پایدار تأیید شد.
- برای این فاز نیازی به تغییر Firmware نیست.

## پروفایل‌های کالیبره‌شده

هر شش پروفایل فعال‌اند؛ `StableDuration = 1250 ms` و `Hysteresis = 1 Lux`:

- Desktop: مرکز `35.8`، تلورانس `±1`، بازه‌ی `34.8..36.8`.
- Login یا DC: مرکز `5.8`، تلورانس `±2.6`، بازه‌ی `3.2..8.4`.
- Character dashboard: مرکز `15.8`، تلورانس `±1`، بازه‌ی `14.8..16.8`.
- Entering-game loading: مرکز `38.3`، تلورانس `±0.5`، بازه‌ی `37.8..38.8`.
- Game: مرکز `26.7`، تلورانس `±1`، بازه‌ی `25.7..27.7`.
- Targeted: مرکز `30`، تلورانس `±1`، بازه‌ی `29..31`.

بازه‌های مؤثر overlap ندارند.

## قرارداد Login و DC

- Login و DC یک پروفایل نوری مشترک دارند؛ Lux علت را تشخیص نمی‌دهد.
- علت recovery توسط caller به‌صورت `Login` یا `Disconnect` داده می‌شود.
- Login مستقیماً جریان مشترک ورود را اجرا می‌کند.
- Disconnect دقیقاً یک `ESC` و سپس همان جریان مشترک Login را اجرا می‌کند.
- ماکروی Login کپی نمی‌شود؛ DC فقط یک prelude دارد.

## اصلاح CI

دو workflow مستقل از الگوی یکسان `light-state-test-${github.run_number}` استفاده می‌کردند. چون run number برای هر workflow مستقل است، collision تگ باعث check قرمز کاذب می‌شد. workflow تکراری حذف شد و AutoCycle تنها بسته‌ساز gated است. پس از اصلاح، همهٔ gateها سبز و Release `light-state-test-269` منتشر شد.

## مرز ایمنی

- Live Watch و classifier فقط مشاهده‌ای و بدون Side Effect هستند.
- هیچ Macro، فشردن کلید، BEEP، `WLUX`، `TRGLUX`، Launch یا Auto Resume از مسیر تشخیص اجرا نمی‌شود.
- قرارداد `ESC` فقط مدل شده و classifier آن را اجرا نمی‌کند.
- گیت اجرایی فاز ۵ باید به‌صورت جداگانه طراحی، تست و تأیید شود.

## گام بعدی

1. merge فاز ۴ فقط پس از تأیید صریح کاربر.
2. شروع فاز ۵ با طراحی قرارداد ایمنی گیت اجرایی، بدون فعال‌سازی Side Effect در گام اول.

## گیت‌های دائمی

1. build اپ بدون خطا.
2. TestRunner با `0 failed`.
3. parity خروجی عادی و AutoCycle.
4. sensitive guard سبز.
5. merge فقط از مسیر PR.
6. تغییر UI فقط بعد از آماده‌شدن Protocol و Bridge typed.
