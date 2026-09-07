# v0.9.53 — تشخیص درست پورت وصل + پاکسازی واقعی تاریخچه‌ی COM

## 1) تشخیص پورت وصل (رفع ایراد گزارش‌شده)

**ریشه:** v0.9.51/52 وصل بودن را فقط از `HKLM\HARDWARE\DEVICEMAP\SERIALCOMM` می‌گرفت.
این منبع برای دستگاه‌های composite (CDC چندواسطه، مودم‌ها، برد در حالت بوت‌لودر) ناقص است،
پس پورت‌های واقعاً وصل با برچسب «تاریخچه» نمایش داده می‌شدند.

ابزار مرجع (AMS USB Studio v3.1) از pyserial ← SetupAPI استفاده می‌کرد، یعنی از خود PnP می‌پرسید.

**اصلاح:** در `BoardCheckupService`

- `DeviceInstanceId(idName, instance)` → `USB\VID_xxxx&PID_xxxx&MI_00\6&...`
- `IsDevicePresent(instanceId)` → `CM_Locate_DevNodeW` از `cfgmgr32.dll`
  (پرچم NORMAL = فقط دستگاه متصل، PHANTOM = می‌شناسد ولی وصل نیست)
- `IsHistoryRow(present, port, live)` — نظر PnP مقدم است؛ SERIALCOMM فقط پشتیبان (و اکنون اجتماع با `SerialPort.GetPortNames()`)
- اگر cfgmgr32 جواب نداد (`null`)، رفتار قبلی حفظ می‌شود — هیچ حذفی کورکورانه انجام نمی‌شود.

## 2) دکمه‌ی پاکسازی که چیزی حذف نمی‌کرد — دو باگ جداگانه

### الف) «رد شد (خارج از خانواده‌های مجاز)»

الگوی مسیر رجیستری فقط `VID_xxxx&PID_xxxx` را می‌پذیرفت، اما بردهای composite پسوند `&MI_00` دارند
→ همه‌ی آن ورودی‌ها بی‌بررسی رد می‌شدند. همچنین لیست مجاز فقط PID بوت‌لودر را داشت، پس `1D50:615F` (اپلیکیشن) رد می‌شد.

اصلاح: الگوی جدید پسونددار + `ParentKeyFromRegPath` + `InstanceIdFromRegPath` + `ExpandFamilies` (PID اپ = بوت ± ۱).
لیست پیش‌نمایش در پنجره هم از همان لیست مجاز استفاده می‌کند، پس دیگر وعده‌ی حذفی که اجرا رد می‌کند نمی‌دهد.

### ب) `Attempted to perform an unauthorized operation`

زیردرخت `SYSTEM\CurrentControlSet\Enum\USB` مالکش SYSTEM است. توکن ادمین، `SeTakeOwnershipPrivilege` و
`SeRestorePrivilege` را **دارد ولی غیرفعال** است، و .NET هرگز فعالشان نمی‌کند — پس تغییر مالکیت شکست می‌خورد (دقیقاً ۰/۶ گزارش شما).

اصلاح: نردبان سه‌پله‌ی `DeletePlan()`

1. `pnputil /remove-device "<instance-id>"` — روش رسمی PnP؛ بدون دست‌زدن به ACL.
2. فعال‌سازی اختیارات با `AdjustTokenPrivileges` و سپس تملیک + حذف درخت.
3. آخرین راه: اجرای `reg delete` در قالب یک تسک یک‌بارمصرف با `/ru SYSTEM`.

هر پله با خواندن دوباره‌ی کلید تأیید می‌شود؛ بیت ComDB فقط برای پورت‌های واقعاً حذف‌شده آزاد می‌شود. بکاپ `.reg` قبل از هر حذف سر جای خود است.

## 3) اصلاح بیلد و تست‌های زنجیره‌ای

- `MainViewModel`: `IsBusyRunning` ← `IsRunning` (همان اصلاح دستی بیلد، دائمی شد).
- ۱۸ ادعای نسخه‌ی hard-coded و دو ادعای ساختار تب به ویزارد/0.9.53 منتقل شدند → انتظار `0 failed`.
- گام ۵۳ با ۲۰ ادعا برای همین دو موضوع اضافه شد.
