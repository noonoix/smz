# Firmware امن Pico برای Light Watch خواندنی

این بسته برای تست Phase 6 ساخته شده و فقط مسیر خواندنی سنسور نور را فعال می‌کند.

## مرز ایمنی

این firmware عمداً ندارد:

- Keyboard یا Mouse HID
- Macro یا اجرای pipeline
- UART به Pro Micro
- Buzzer
- actuator، موتور، رله یا فرمان اجرایی

فرمان‌های مجاز فقط این‌ها هستند:

- `PING`
- `LUX?`
- `HALT`
- `BYE`

هر فرمان دیگر با `ERR|READONLY|...` رد می‌شود و هیچ side effect ندارد.

## سخت‌افزار مجاز

فقط این setup را استفاده کنید:

- Raspberry Pi Pico معمولی، نه Pico W مگر firmware جداگانه ساخته شود
- BH1750 / GY-30
- USB

سیم‌های سنسور طبق این قرارداد هستند:

- `GP20` → SDA
- `GP21` → SCL
- `3V3` → VCC
- `GND` → GND
- پایهٔ ADDR سنسور → GND برای آدرس `0x23`

هیچ Pro Micro، BSS138، Buzzer، Keyboard/HID یا actuator نباید وصل باشد.

## نصب

1. فایل رسمی CircuitPython مخصوص **Raspberry Pi Pico معمولی** را فقط به‌عنوان runtime نصب کنید.
2. پس از ظاهرشدن درایو `CIRCUITPY`، فایل‌های همین پوشه را در ریشهٔ آن کپی کنید:
   - `boot.py`
   - `code.py`
3. فایل یا پوشهٔ دیگری، مخصوصاً `lib/adafruit_hid`، اضافه نکنید.
4. Pico ری‌استارت می‌شود و HID را غیرفعال می‌کند.
5. بعد از نصب، ابتدا با یک setup فقط‌خواندنی و بدون Pro Micro آن را آزمایش کنید.

## پاسخ‌های مورد انتظار

`PING` باید پاسخی مانند زیر بدهد:

```text
OK|PONG|pico-light-readonly 1.0.0|role=light-readonly|hid=off|actuator=off
```

`LUX?` باید پاسخی مانند زیر بدهد:

```text
OK|LUX|seq=1|lux=123.4|mode=hires|sensor=ok
```

اگر سنسور وصل نباشد، پاسخ باید `ERR|NOSENSOR|LUX` باشد؛ هیچ فرمان دیگری اجرا نمی‌شود.

## هشدار

این بسته UF2 جدید نیست؛ `adafruit-circuitpython-raspberry_pi_pico-en_US-10.3.0.uf2` فقط runtime عمومی CircuitPython است. کد امن پروژه در `boot.py` و `code.py` قرار دارد. فایل‌های قدیمی keyboard/macro یا template اجرایی را روی این Pico کپی نکنید.
