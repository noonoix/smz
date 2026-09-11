تست HostUSB Auto Resume v5 - بدون Helper ویندوز و بدون بازر

هدف:
Pro Micro 2.6 وضعیت USB/HID ویندوز را با EVT|HOSTUSB|DOWN/SUSPEND/UP به Pico می‌دهد.
Pico فقط با marker مسلح + چرخه قطع/وصل واقعی + پایداری اتصال، Resume می‌کند.
Fallback داخلی Pico برابر supervisor.runtime.usb_connected است.

مراحل:
1) ابتدا ams_board26.ino را کامپایل و با همان روش ISP قبلی روی Pro Micro فلش کن.
2) فایل‌های پوشه CIRCUITPY را روی ریشه درایو Pico کپی و Replace کن. پوشه lib و فایل pico-calibration.json خودت را حذف یا جایگزین نکن.
3) هر دو برد را قطع و وصل کن؛ در کنسول باید HOSTUSB=1 در VER/PONG یا خط cycle: arm host USB UP دیده شود.
4) GP4 را فقط یک بار بزن؛ LED باید همان بار اول روشن شود.
5) پلن آزمایشی بعد از 20 ثانیه Restart را آغاز می‌کند. صفحه مانع Restart حدود 5.2 تا 6 ثانیه بعد با Shift+Tab واقعی و Enter تأیید می‌شود.
6) پس از بالا آمدن Windows و پایدارشدن USB، 3 تا 5 ثانیه بعد باید cycle: AUTO_RESUME start ثبت و Root اجرا شود.
7) سپس GP4 را بزن تا چرخه دوم شروع نشود.

گیت منفی:
اگر Windows را عادی بالا آوردی و marker مسلح وجود نداشت، Root نباید خودکار شروع شود.

نکته: این روش هیچ exe، سرویس، Scheduled Task، Startup entry یا Registry key روی Windows نمی‌سازد؛ ولی لاگ عادی Restart/USB خود Windows قابل حذف نیست.
