# BUILD-ONLY v0.9.51a — فقط build / test / publish (بدون هیچ تصمیم کدنویسی)

هات‌فیکس v0.9.51: یک خطا گزارش شد — `CS1009: Unrecognized escape sequence` در
`tests/TestRunner.cs` خط ۲۹۱۰ (پیام assertion با `Enum\USB` در رشته‌ی غیر-verbatim). **در این
بسته اصلاح شده** (همان خط verbatim است). هیچ تغییر دیگری نیست؛ نسخه‌ها همان 0.9.51.
این تنها BUILD-ONLY داخل زیپ است — قدیمی‌ها حذف شدند (درس 50b: دو BUILD-ONLY کنار هم ممنوع).

کار تو فقط سه مرحله است. **هیچ فایلی را ویرایش نکن.** اگر چیزی شکست خورد، متن کامل خطا را برگردان و توقف کن.

## مرحله ۱ — جایگزینی کامل درخت (هرگز selective merge نه)
## مرحله ۲ — build و تست

```powershell
cd ams-shell
dotnet build -c Release
cd ..\tests
dotnet run 2>&1 | Tee-Object test-output-v0.9.51a.txt
```

**ملاک پذیرش:** صفر خطای build + خط آخر `0 failed` + هر **۱۶** خط PASS ِ گام ۵۱ (`v0.9.51: …`).
عدد کل حدود `522 ± 13` طبیعی است (sweep تصادفی).

## مرحله ۳ — publish و ریلیز

```powershell
cd ..\ams-shell\src\Ams.UI
dotnet publish -c Release -r win-x64 --self-contained false
```

زیپ ریلیز: `Classroom-Studio-v0.9.51-release.zip`. قبل از ارسال: **FileVersion = 0.9.51.0** ·
حضور `caterina\` و `tools\` و `bridge.py` (هش `e72530b2…`) · صفر فایل `.cs`/`.xaml` در ریلیز.
ریلیز + `test-output-v0.9.51a.txt` را برگردان.

## تست بصری v0.9.51 (موردبه‌مورد گزارش بده)

۱) اسکن: ردیف‌های تاریخچه 🕘 علامت دارند و شمارش «N وصل · M تاریخچه» چاپ می‌شود · ۲) چکاپ
کامل روی فانتوم‌ها ۲ ثانیه تلف نمی‌کند و «پروگرمر آنلاین» فقط زنده‌هاست · ۳) 🧹: dry-run فقط
فانتوم‌های خانواده‌ی ما (ZyXEL/Samsung هرگز) ← تأیید ← UAC ← لاگ حذف/بکاپ ← اسکن دوباره
(فایل com-cleanup-backup-*.reg کنار exe) · ۴) تب ۲: کارت «مشخصات برد» بالای پیش‌نمایش و همگام
با تب ۱ · ۵) نکات فارسی راست‌چین.
