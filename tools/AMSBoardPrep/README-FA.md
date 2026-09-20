# AMS Board Prep Debug

نسخهٔ مستقل برای آماده‌سازی دستی **یک برد در هر نوبت**. این برنامه داخل Classroom Studio اجرا نمی‌شود و برای تست/دیباگ روند هویت USB، نصب Arduino IDE، ISP، آپدیت Application و چکاپ ساخته شده است.

## روند

1. در تب هویت، VID/PID/Product/Manufacturer/Serial را وارد کنید و فقط یک HEX بسازید.
2. همان Profile را در Sketchbook نصب کنید.
3. همان `Caterina-<Serial>.hex` را با ArduinoISP روی برد فلش کنید.
4. Application را در Arduino IDE با همان Profile کامپایل کنید و App-only HEX را از مسیر USB آپلود کنید.
5. چکاپ را اجرا کنید؛ Serial و PID باید با Profile فعال برابر باشند.

این نسخه عمداً Count یا تولید دسته‌ای ندارد. قبل از استفاده، Arduino IDE و Serial Monitor را هنگام ISP ببندید و در مرحلهٔ ISP پورت پروگرامر را انتخاب کنید.

## مرحلهٔ ۶ — فلش اضطراری Application با ISP

اگر برد USB/COM ندارد، Arduino IDE لازم نیست؛ یک Application-only HEX از قبل کامپایل‌شده را در تب ۶ انتخاب کنید. ابزار فقط صفحات زیر `0x7000` را می‌نویسد و Bootloader، Lock، Fuse و EEPROM را تغییر نمی‌دهد. این مرحله فایل `.ino` را کامپایل نمی‌کند و HEX باید قبلاً با همان Product/Serial/VID/PID ساخته شده باشد.
