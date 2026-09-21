# Guard Trace Collector

ابزار مستقل و قابل‌حمل Windows برای دریافت زندهٔ رویدادهای Pico Guard.

## استفاده

1. `GuardTraceCollector.exe` را اجرا کنید.
2. برنامه فقط پورت‌هایی را انتخاب می‌کند که به `PING` با نقش `brain` پاسخ دهند.
3. رویدادهای USB را در صفحه و فایل `traces/guard-trace-*.log` ثبت می‌کند.
4. برای دریافت ژورنال ذخیره‌شدهٔ قبلی Pico، اجرا کنید:

```powershell
GuardTraceCollector.exe --history
```

برای انتخاب دستی پورت:

```powershell
GuardTraceCollector.exe --port COM31
```

ابزار بعد از اتصال، به‌جز `PING` برای شناسایی و در حالت `--history` فرمان `DEBUGGET`، هیچ فرمان اجرایی یا Guard/HID ارسال نمی‌کند. حجم هر فایل حداکثر ۱MB و فقط پنج فایل آخر نگه داشته می‌شود.

رویدادهای مهمی که باید دیده شوند:

```text
EVT/DEBUG/GP4/short-start
EVT/DEBUG/STATE/desktop/lux=...
EVT/DEBUG/ROUTE/start/desktop_steps.txt
EVT/DEBUG/ROUTE/complete/desktop_steps.txt
EVT/DEBUG/FAIL/...
```
