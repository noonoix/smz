# Classroom Studio — وضعیت زنده‌ی پروژه

> منبع حقیقت جاری پروژه؛ تاریخچه‌ی کامل در صفحه‌ی Notion پروژه نگهداری می‌شود.

## وضعیت لحظه‌ای — ۲۰۲۶-۰۹-۱۵

- مخزن فعال: `kirobesaban/smc-1`.
- شاخه‌ی پایدار: `main`.
- head پایدار: `a1aa9e552cd52ffcf676b596199db81efac9c51f`.
- آخرین Release معتبر پایدار: `ci-115` با `770 passed, 0 failed`.
- SHA-256 فایل پایدار `Classroom-Studio-release.zip`: `E8BBC4FFF05118EB9F9A7EA0FE6AA38F8661917DE8C9CFEB6BCDBDE066CFDF2E`.
- خط ریلیز اپ: `0.9.67 / PLAN|2`.
- شاخه‌ی ارتقای جاری: `feature/light-state-profiles`.
- Draft PR جاری: `#158`، به‌صورت stacked روی `feature/status-tab-light-watch` / PR `#157`.
- آخرین بسته‌ی تست فاز ۴: `light-state-test-257` از commit `11e0a9905ccbc179288c62b1065892ed9f9519aa`.
- SHA-256 بسته‌ی تست ۲۵۷: `641EE80C5726B6DD284D6FD83BF671CE828AB3A927743677A3DC3F1CD0028B2E`.

## معماری تثبیت‌شده

- Classroom Studio محیط ساخت، تنظیم، کالیبراسیون، تست و Export است.
- Pico مغز اجرایی مستقل، مجری Keyboard، سنسور نور BH1750 و موتور پرتابل است.
- Pro Micro بازوی Mouse و Sound Sensor است و از طریق UART با Pico کار می‌کند.
- BH1750 روی Pico با `SDA=GP20`، `SCL=GP21` و آدرس `0x23` است.
- قراردادهای اجرایی `WLUX` و `TRGLUX` و قرارداد کالیبراسیون `LCAL` حفظ می‌شوند.

## ارتقای جاری: Status و Live Watch نور

فاز صفر در `ams-shell/src/Ams.UI/docs/light-telemetry-phase-zero.md` ثبت شده است.

ترتیب اجرا:

1. فرمان فقط‌خواندنی `LUX?` و تست Firmware، بدون تغییر XAML — کامل.
2. API typed در Bridge و Watch Service بدون overlap — کامل.
3. تب مستقل Status با Lux زنده، health، نمودار و آمار — کامل و تأییدشده روی Windows / COM5.
4. Light State Profile و classifier با stable duration، hysteresis و overlap guard — کامل و تأییدشده روی Windows.
5. تست نرم‌افزاری و سخت‌افزاری BH1750 — Gate عمومی کامل؛ کالیبراسیون صحنه‌های واقعی جداگانه انجام می‌شود.
6. QA بصری، CI با `0 failed` و Release تست — کامل برای فاز ۴؛ PR تا پایان کالیبراسیون واقعی و جمع‌بندی stacked Draft می‌ماند.

## نتیجه‌ی QA سخت‌افزاری Windows — فاز ۴

- اتصال خودکار Pico روی `COM5` با Firmware `pico-light 0.9.64h` موفق بود.
- Bridge پاسخ `LUX?` را به‌صورت typed با `OK|LUX|...` دریافت کرد؛ Timeout نسخه‌ی ۲۵۰ رفع شد.
- نمونه‌ها در بازه‌ی مشاهده‌شده از `seq=106` تا `seq=443` پیوسته بودند.
- رویدادهای `EVT|HOSTUSB|UP` با پاسخ‌های Lux اشتباه نشدند.
- نمودار، کمینه، بیشینه، میانگین و spread با تغییر واقعی نور به‌روز شدند.
- توقف Watch، حفظ آخرین نمودار و تبدیل freshness به «داده قدیمی» تأیید شد.
- classifier مقدار حدود `3.3 Lux` را پس از StableDuration به «صفحه لود ورود به بازی» نگاشت؛ confidence نمایشی `15%` بود.
- UI فاز ۴ در RTL و عرض کم نمایش داده شد: State، confidence، overlap warning، شش پروفایل و calibration.
- کالیبراسیون ۵ ثانیه‌ای با ۱۸ نمونه، مرکز `3.3` و تلورانس پیشنهادی `0.5` ساخت و بدون اقدام صریح overwrite نکرد.
- Apply، Reset، انتخاب مجدد پروفایل calibration، Save و persistence پس از restart تأیید شدند.
- ورودی منفی، `NaN` و فیلد خالی رد شدند؛ ورودی اعشاری `1.5` پذیرفته و ذخیره شد.
- Pico و محتوای `CIRCUITPY` صحیح‌اند و برای این فاز نیازی به تغییر Firmware نیست.

## پروفایل‌های اولیه فاز ۴

اعداد زیر فرضی و قابل‌ویرایش‌اند؛ تلورانس پیش‌فرض همه `±2 Lux` است:

- Desktop: مرکز `0`، بازه‌ی clamp‌شده‌ی `0..2`.
- Login یا DC: مرکز `25`، بازه‌ی `23..27`.
- Character dashboard: مرکز `31`، بازه‌ی `29..33`.
- Entering-game loading: مرکز `5`، بازه‌ی `3..7`.
- Game: مرکز `26`، بازه‌ی `24..28`.
- Targeted: مرکز `20`، بازه‌ی `18..22`.

Login/DC و Game بین `24..27 Lux` overlap دارند. classifier باید `Ambiguous` برگرداند و هرگز براساس ترتیب پروفایل برنده انتخاب نکند.

## قرارداد Login و DC

- Login و DC یک پروفایل نوری مشترک دارند؛ Lux علت را تشخیص نمی‌دهد.
- علت recovery توسط caller به‌صورت `Login` یا `Disconnect` داده می‌شود.
- Login مستقیماً جریان مشترک ورود را اجرا می‌کند.
- Disconnect دقیقاً یک `ESC` برای بستن popup اجرا می‌کند و سپس همان جریان مشترک Login را ادامه می‌دهد.
- ماکروی Login کپی نمی‌شود؛ DC فقط یک prelude دارد.

## مرز ایمنی

- Live Watch کاملاً مشاهده‌ای و بدون Side Effect است.
- Watch حق اجرای Macro، فشردن کلید، BEEP یا overwrite کالیبراسیون را ندارد.
- Light State و confidence در فاز ۴ فقط نمایشی‌اند.
- گیت اجرایی Launch/Auto Resume تا قرارداد ایمنی جداگانه فعال نمی‌شود.
- قرارداد `ESC` فقط مدل شده و classifier آن را اجرا نمی‌کند.

## گام بعدی

1. کالیبراسیون واقعی شش وضعیت در صفحه‌های واقعی برنامه/بازی و ثبت Lux هر وضعیت.
2. بررسی و رفع overlap واقعی Login/DC و Game با داده‌ی کالیبره‌شده.
3. تبدیل اصلاح response correlation در Bridge از wrapper بسته‌بندی به patch canonical همراه regression test مستقیم.
4. جمع‌بندی PRهای stacked؛ PR `#158` تا پایان این موارد Draft می‌ماند.
5. فقط پس از تأیید فاز ۴، ورود به فاز ۵ Hardware Acceptance و طراحی گیت اجرایی جداگانه.

## گیت‌های دائمی

1. build اپ بدون خطا.
2. TestRunner با `0 failed`.
3. parity خروجی عادی و AutoCycle.
4. گیت sensitive guard سبز.
5. merge فقط از مسیر PR؛ هیچ push مستقیمی به `main`.
6. تغییر UI فقط بعد از آماده‌شدن Protocol و Bridge typed.
