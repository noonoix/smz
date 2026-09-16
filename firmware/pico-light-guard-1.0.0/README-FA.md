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
- دکمهٔ Start/Stop: `GP4` به `GND` با pull-up داخلی
- دکمهٔ Pass/Next: `GP3` به `GND` با pull-up داخلی
- passive piezo: `GP6`

هیچ Pro Micro، BSS138، UART، HID، keyboard، mouse، buzzer قدیمی، motor، relay یا actuator به این setup وصل نشود.

## رفتار دکمه‌ها

- نگه‌داشتن `GP4` به‌مدت ۳ ثانیه: ورود به حالت کالیبراسیون.
- فشار کوتاه `GP4` خارج از calibration: روشن/خاموش‌کردن Guard.
- فشار کوتاه `GP4` داخل calibration: لغو calibration.
- فشار کوتاه `GP3` در حالت آمادهٔ هر مرحله: شروع نمونه‌برداری ۵ ثانیه‌ای.
- فشار کوتاه بعد از موفقیت هر مرحله: رفتن به موقعیت بعدی.
- پس از موفقیت مرحلهٔ ششم و فشار بعدی `GP3`: ذخیرهٔ شش موقعیت و پخش صدای موفقیت.
- شش موقعیت به‌ترتیب:
  1. Desktop
  2. Login/DC
  3. Character Dashboard
  4. Entering Game Loading
  5. Game
  6. Targeted

Login و DC یک کالیبر نوری مشترک دارند؛ تفاوت DC باید در pipeline/action برنامه باشد، نه در نورسنجی.

## کالیبراسیون

هر موقعیت با ۵ ثانیه نمونه‌برداری می‌شود. firmware median، کمینه، بیشینه و spread را محاسبه می‌کند. اگر spread از حد مجاز بیشتر باشد، مرحله رد می‌شود و باید دوباره انجام شود. پس از موفقیت، `center` و `tolerance` ذخیره می‌شوند.

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
