# GuardHardwareMonitor

مانیتور تشخیصی و **فقط خواندنی** برای بررسی رفتار Pico و در صورت نیاز Pro Micro.

## قابلیت‌ها

- ثبت تغییرات پورت‌های COM؛
- ارسال خودکار فقط `PING` برای شناسایی Pico؛
- ثبت تمام خطوط خام دریافتی با زمان میلی‌ثانیه؛
- دسته‌بندی رویدادهای GP4، GP3، CAL، STATE، ROUTE، FAIL و ARM؛
- ثبت Disconnect/Reconnect و وضعیت Heartbeat؛
- در حالت `--history` ارسال فقط `DEBUGGET` برای خواندن Trace ذخیره‌شده؛
- امکان مانیتور یک پورت دوم با `--arm-port` بدون ارسال هیچ فرمانی.

این ابزار هیچ‌کدام از `GUARD|ON`، `HALT`، `KEY`، `RMOUSE`، `BEEP` یا فرمان HID را ارسال نمی‌کند.

## اجرا

```powershell
GuardHardwareMonitor.exe
GuardHardwareMonitor.exe --port COM31
GuardHardwareMonitor.exe --port COM31 --history
GuardHardwareMonitor.exe --port COM31 --arm-port COM40
GuardHardwareMonitor.exe --seconds 120
```

خروجی در پوشهٔ `diagnostics` کنار فایل اجرایی ذخیره می‌شود.
