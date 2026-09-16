# Firmware ترکیبی Pico Guard + Portable Executor — Phase 7

این firmware برای یک Raspberry Pi Pico معمولی طراحی شده است. Pico پس از کپی دستی bundle به `CIRCUITPY`، هم Guard نوری و هم اجرای Portable Steps را بر عهده دارد. Classroom Studio فقط محل authoring، تست دستی با RunEngine، export و همگام‌سازی revision است؛ پس از قطع کامپیوتر runtime به Windows وابسته نیست.

## سخت‌افزار مجاز

- Raspberry Pi Pico معمولی، نه Pico W
- BH1750 / GY-30:
  - `SDA` -> `GP20` / physical pin 26
  - `SCL` -> `GP21` / physical pin 27
  - `VCC` -> `3V3`
  - `GND` -> `GND`
  - `ADDR` -> `GND` / address `0x23`
- دکمه آبی مربعی: `GP4` به `GND` با pull-up داخلی
- دکمه زرد دایره‌ای: `GP3` به `GND` با pull-up داخلی
- passive piezo: `GP6`
- UART0 به Arduino arm: `GP16 TX -> Arduino RX`، `GP17 RX <- Arduino TX`، GND مشترک، `57600 8N1`
- USB HID خود Pico مسیر keyboard برای Portable Steps است.

Arduino arm حذف نمی‌شود و مسئول mouse و sound است. هیچ Pro Micro یا BSS138 لازم نیست.

## رفتار دکمه‌ها

### Portable runtime

- فشار کوتاه آبی `GP4`: Start/Stop اجرای Portable plan
- فشار کوتاه زرد `GP3`: Pause/Resume اجرای Portable plan
- نگه‌داشتن آبی `GP4` به‌مدت ۳ ثانیه، فقط وقتی runtime متوقف است: ورود به calibration

### Calibration

- فشار کوتاه آبی: رفتن به profile بعدی؛ در profile ششم همان profile باقی می‌ماند.
- نگه‌داشتن آبی ۳ ثانیه: خروج امن.
- فشار کوتاه زرد پیش از sample: شروع sample پنج‌ثانیه‌ای.
- فشار کوتاه زرد بعد از sample موفق: ذخیره profile انتخاب‌شده.
- navigation یا خروج هنگام sample موفق ذخیره‌نشده مسدود می‌شود.
- eventهای calibration هرگز به Start/Stop یا Pause/Resume runtime تبدیل نمی‌شوند.

شش profile به‌ترتیب:

1. `desktop`
2. `login-or-dc`
3. `character-dashboard`
4. `entering-game-loading`
5. `game`
6. `targeted`

Login و DC یک calibration record مشترک دارند؛ تفاوت آن‌ها context انتقال است، نه نورسنجی.

## Bundle و runtime

فایل‌های روی `CIRCUITPY` منبع حقیقت runtime هستند. Bundle معتبر شامل این موارد است:

- `code.py`, `boot.py`
- `plan.txt`
- `desktop_steps.txt`, `login_or_dc_steps.txt`, `character_dashboard_steps.txt`, `entering_game_loading_steps.txt`, `game_steps.txt`, `targeted_steps.txt`, `resumable_steps.txt`
- `plan_engine.py` و runtime moduleهای لازم
- `guard-transition.json`, `guard-calibration.json`
- `SHA256SUMS.txt`

Loader پیش از استفاده، manifest، هفت route، شش profile، revision و runtime files را بررسی می‌کند و bundle ناقص یا stale را رد می‌کند.

## Transition policy

- progression اصلی strictly ordered است: Desktop -> Login/DC -> Character Dashboard -> Entering Game/Loading -> Game.
- DC در stageهای فعال یا Targeted به stage 2 برمی‌گردد و بعد progression را از Login/DC ادامه می‌دهد.
- Targeted stage ششم نیست؛ side-state است، Steps خودش را یک بار اجرا می‌کند و پس از مشاهده fresh و stable Game بدون اجرای دوباره Game Steps برمی‌گردد.
- stable optical state تکراری دوباره route را اجرا نمی‌کند.
- Stop/HALT اجرای plan را متوقف و arm را safely release می‌کند.

## CALGET و CALSET

```text
CALGET
CALSET|<revision>|<profile-id>|<center>|<tolerance>|<stable-ms>
```

revision باید token امن باشد؛ profile فقط یکی از شش ID canonical است و مقادیر عددی باید finite و non-negative باشند. انتشار CALSET هر دو `guard-transition.json` و `guard-calibration.json` را به‌صورت موقت/اتمی می‌نویسد، reload و validation می‌کند و در خطا rollback دارد.

## فرمان‌های USB

- `PING`
- `LUX?`
- `CALGET`
- `CALSET|...`
- `GUARD|ON`
- `GUARD|OFF`
- `HALT`

پاسخ هویت مورد انتظار:

```text
OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6
```

`GUARD|ON` فقط وقتی plan را فعال می‌کند که bundle معتبر باشد؛ transition و route execution روی Pico انجام می‌شود. Guard eventها هیچ‌وقت RunEngine یا دکمه‌های Run/Stop دسکتاپ را trigger نمی‌کنند.

## وضعیت پذیرش

CI و Windows build جایگزین Hardware Acceptance نیستند. این package هنوز نباید روی setup قبلی نصب یا flash شود. پذیرش فیزیکی جداگانه باید با SHA دقیق package، wiring مصوب، evidence کالیبراسیون، CALSET/CALGET، transitionهای ordered، Targeted/DC، keyboard HID، Arduino mouse/sound و مسیر HALT انجام شود. تا آن زمان PR Draft می‌ماند و هیچ Hardware Acceptance یا production-readiness ادعایی مجاز نیست.
