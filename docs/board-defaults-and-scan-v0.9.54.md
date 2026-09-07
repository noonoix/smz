# v0.9.54 — مشخصات پیش‌فرض دستگاه‌ها، فرم قابل ویرایش مشخصات برد، اسکن پورت تمیز

## 1) انتخاب دستگاه = پر شدن خودکار همه‌ی فیلدها

`BoardHexService.DefaultsFor(key)` برای هر هویت، یک مجموعه‌ی کامل می‌دهد:
شناسه‌ی برد، نام برد، VID بوت‌لودر، PID بوت‌لودر، PID اپلیکیشن (= بوت + ۱)، نام محصول و سازنده.

| دستگاه | VID:PID بوت | PID اپ | نام محصول | سازنده |
|---|---|---|---|---|
| پیش‌فرض AMS | 1D50:615E | 615F | AMS Macro Studio | AMS |
| STM32 Virtual COM | 0483:5740 | 5741 | STM32 Virtual COM Port | STMicroelectronics |
| Seeed XIAO | 2886:802F | 8030 | Seeed XIAO | Seeed |
| Microchip CDC Demo | 04D8:000A | 000B | CDC RS-232 Emulation Demo | Microchip |
| LEGO Education SPIKE | 0694:0009 | 000A | LEGO Technic Large Hub | LEGO Education |
| M5Stack Core | 303A:1001 | 1002 | M5Stack Core | M5Stack |

مقادیر از دیتابیس USB-ID و مستندات سازندگان گرفته شده‌اند، همه ASCII و کوتاه‌تر از ۲۹ کاراکتر (محدودیت `ValidateUsbString`).

## 2) فرم مشخصات برد در قدم ۲ بازگشت

درست مانند تب ۲ ابزار مرجع: هفت فیلد (`TxtBoardId`، `TxtBoardName`، `TxtBootVid`، `TxtBootPid`،
`TxtAppPid`، `TxtBoardProduct`، `TxtBoardManuf`)، خودکار پر می‌شوند و قابل ویرایشند؛ پیش‌نمایش boards.txt
زیرشان با هر تغییر تازه می‌شود. دو دکمه: «بازنشانی به پیش‌فرض دستگاه» و «به‌روزرسانی پیش‌نمایش».

- `BoardSpecsFromUi()` تنها منبع ساخت بلوک است؛ فیلد خالی = مقدار هویت انتخاب‌شده.
- شناسه‌ی برد با `SanitizeBoardId` به قالب مجاز آردوینو (`[a-z0-9_]`) درمی‌آید.
- نصب و حذف هم همین شناسه را می‌برند، پس حذف، دقیقاً همان بلوکی را می‌برد که نصب شده بود.

## 3) حذف پنج دستگاه از لیست

BBC micro:bit (هر دو نسخه)، Calliope mini، Adafruit Circuit Playground، ESP32-S2 و Raspberry Pi Pico
از `DeviceModes` و از `KnownIdentities` چکاپ حذف شدند. شش هویت ماند.

## 4) اسکن پورت: پیش‌فرض = فقط پورت‌های واقعاً وصل

مشکل گزارش‌شده: با یک برد متصل، لیست ۱۰ ردیف نشان می‌داد (۸ مودم ZyXEL و ۱ سامسونگ که
متعلق به ما نیستند)، و نوار وضعیت می‌گفت «۱۰ پورت» در حالی که پاکسازی می‌گفت تاریخچه‌ای نیست.

- `BoardCheckupService.VisibleRows(rows, showHistory)` — به‌صورت پیش‌فرض فقط ردیف‌های متصل.
- `ScanSummaryLine(rows, showHistory)` — دو عدد جداگانه: وصل و تاریخچه‌ی پنهان‌شده.
- تیک `نمایش تاریخچه` در قدم ۴ لیست را بدون اسکن مجدد بازمی‌سازد (`RenderPortRows`).
- نوار وضعیت فقط پورت‌های وصل را می‌شمارد.

منطق تشخیص دستگاه دست‌نخورده ماند (همان PnP نسخه‌ی 0.9.53)؛ فقط نمایش و شمارش درست شد.
