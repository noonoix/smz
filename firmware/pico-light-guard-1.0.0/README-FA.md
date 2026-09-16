# Firmware نگهبان نور — Phase 7

این firmware یک مسیر جدا از `pico-light-readonly` است. هدف آن مشاهدهٔ دائمی نور، کالیبراسیون شش موقعیت و اعلام state به Classroom Studio است؛ هیچ execution انجام نمی‌دهد.

## سخت‌افزار مجاز

- Raspberry Pi Pico معمولی، نه Pico W
- BH1750 / GY-30
- `SDA` → `GP20` / physical pin 26
- `SCL` → `GP21` / physical pin 27
- `VCC` → `3V3`
- `GND` → `GND`
- `ADDR` → `GND` / address `0x23`
- دکمهٔ آبی مربعی Start/Stop: `GP4` به `GND` با pull-up داخلی
- دکمهٔ زرد دایره‌ای Pass/Save: `GP3` به `GND` با pull-up داخلی
- passive piezo: `GP6`

هیچ Pro Micro، BSS138، UART، HID، keyboard، mouse، buzzer قدیمی، motor، relay یا actuator به این setup وصل نشود.

## رفتار دکمه‌ها

- نگه‌داشتن دکمهٔ آبی `GP4` به‌مدت ۳ ثانیه خارج از calibration: ورود به کالیبراسیون در موقعیت اول.
- فشار کوتاه دکمهٔ آبی داخل calibration: رفتن به موقعیت بعدی از شش موقعیت؛ در موقعیت ششم، همان موقعیت باقی می‌ماند.
- نگه‌داشتن دوبارهٔ دکمهٔ آبی به‌مدت ۳ ثانیه داخل calibration: خروج امن از calibration و نگه‌داشتن فقط موقعیت‌هایی که با زرد ذخیره شده‌اند.
- فشار کوتاه دکمهٔ آبی خارج از calibration: روشن/خاموش‌کردن Guard observation.
- فشار کوتاه دکمهٔ زرد در موقعیت آماده: شروع نمونه‌برداری پنج‌ثانیه‌ای.
- فشار کوتاه دکمهٔ زرد پس از پایان موفق نمونه‌برداری: ذخیرهٔ همان موقعیت در حافظهٔ محلی.
- جابه‌جایی با آبی یا خروج با آبی در حالی که یک نمونهٔ موفق هنوز با زرد ذخیره نشده، مسدود می‌شود تا داده دور ریخته نشود.
- بعد از ذخیره، بازر صدای موفقیت همان موقعیت را پخش می‌کند و بازرِ موقعیت بعدی هنگام ورود، نوت مخصوص خودش را پخش می‌کند.
- اگر هر شش موقعیت در همان جلسه ذخیره شوند، success melody کلی نیز پخش می‌شود؛ خروج همچنان با نگه‌داشتن آبی انجام می‌شود.
- اصلاح جزئی مجاز است: مثلاً می‌توان فقط به `character-dashboard` رفت، نمونه گرفت، با زرد ذخیره کرد و با نگه‌داشتن آبی خارج شد؛ پنج موقعیت دیگر بدون تغییر باقی می‌مانند.

شش موقعیت به‌ترتیب:

1. Desktop
2. Login/DC
3. Character Dashboard
4. Entering Game Loading
5. Game
6. Targeted

Login و DC یک کالیبر نوری مشترک دارند؛ تفاوت DC باید در pipeline/action برنامه باشد، نه در نورسنجی.

## کالیبراسیون

هر موقعیت با ۵ ثانیه نمونه‌برداری می‌شود. firmware median، کمینه، بیشینه و spread را محاسبه می‌کند. اگر spread از حد مجاز بیشتر باشد، مرحله رد می‌شود و همان موقعیت برای تلاش دوباره باقی می‌ماند. پایان موفق نمونه‌برداری یک صدای موفقیت موقعیتی دارد، اما مقدار تا فشار دکمهٔ زرد ذخیره‌شده تلقی نمی‌شود.

لغو/خروج با نگه‌داشتن آبی فقط نتایج تأییدشده با زرد را حفظ می‌کند و نمونهٔ ذخیره‌نشده را کنار می‌گذارد. اگر کاربر بخواهد مقدار ذخیره‌شده را به Classroom Studio منتقل کند، برنامه باید شش مقدار منبع حقیقت خود را با revision جدید از طریق `CALSET` همگام کند.

منبع اصلی کالیبراسیون Classroom Studio است. برنامه می‌تواند برای هر profile فرمان زیر را به Pico بفرستد:

```text
CALSET|<revision>|<profile-id>|<center>|<tolerance>|<stable-ms>
```

شناسه‌های مجاز:

```text
desktop
login-or-dc
character-dashboard
entering-game-loading
game
targeted
```

## فرمان‌های USB

فرمان‌های قابل استفاده:

- `PING`
- `LUX?`
- `CALGET`
- `CALSET|...`
- `GUARD|ON`
- `GUARD|OFF`
- `HALT`
- `BYE`

`GUARD|ON` فقط مشاهده و اعلام `EVT|GUARD|...` را فعال می‌کند. هیچ فرمانی برای Run، Launch، Recovery، Auto Resume، Keyboard، Mouse، HID یا actuator در این firmware وجود ندارد.

## پاسخ هویت مورد انتظار

```text
OK|PONG|pico-light-guard 1.0.0|role=light-guard|hid=off|uart=off|actuator=off|sensor=BH1750|button=GP4,GP3|buzzer=GP6|profiles=6
```

این بسته جایگزین firmware read-only قبلی نیست و هنوز به‌تنهایی پذیرش سخت‌افزاری Guard را کامل نمی‌کند. بعد از تکمیل adapter برنامه، تست قرارداد، تست نویز/قطع سنسور و تست فیزیکی جداگانه لازم است.
