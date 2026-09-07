# BUILD-ONLY v0.9.50a — فقط build / test / publish (بدون هیچ تصمیم کدنویسی)

این بسته **سورس کامل v0.9.50a** است — همان v0.9.50 با **یک اصلاح XAML** (هات‌فیکس شکست
build). کار تو فقط سه مرحله است. **هیچ فایلی را ویرایش نکن، هیچ باگی را «فیکس» نکن.**
اگر چیزی شکست خورد، متن کامل خطا را برگردان و توقف کن.

## چه چیزی نسبت به v0.9.50 عوض شده (فقط برای اطلاع — دست‌کاری نکن)

- **فقط یک فایل:** `ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml` — دو `RadioButton`
  (`RadioSketchbook`، `RadioBoardsTxt`) که `TextWrapping="Wrap"` را مستقیم داشتند و باعث
  `error MC3072` در خط ۱۳۹ می‌شدند. حالا متن داخل `<RadioButton.Content><TextBlock …
  TextWrapping="Wrap"/></RadioButton.Content>` است؛ رفتار wrap حفظ شده، هندلرها و نام‌ها
  همان‌اند. code-behind فقط `IsChecked` می‌خواند.
- شماره‌ی نسخه عمداً **همان `0.9.50`** است (روش v0.9.39a)؛ بنر و csproj دست‌نخورده.
- فایل‌های مستند اضافه‌شده: `docs/board-prep-xaml-hotfix-v0.9.50a.md`، همین فایل، و ورودی
  انتهای `MEMORY.md`.
- `bridge.py` دست‌نخورده (sha256 باید همان `e72530b2…` بماند).

## مرحله ۱ — جایگزینی کامل درخت

قانون طلایی ۱: **هرگز selective merge نه.** محتوای زیپ را روی یک پوشه‌ی تمیز extract کن
(درخت قبلی را کامل پاک کن و از زیپ دوباره بساز).

## مرحله ۲ — build و تست

```powershell
cd ams-shell
dotnet build -c Release
```

انتظار: **۰ خطا**. (دو warning شناخته‌شده‌ی `CS8629` روی VisionService.cs از قبل هستند.)

```powershell
cd ..\tests
dotnet run 2>&1 | Tee-Object test-output-v0.9.50.txt
```

**ملاک پذیرش (قاعده‌ی جدید پروژه):** خط آخر باید `0 failed` بگوید و هر **۱۷** خط PASS ِ
گام ۵۰ (`v0.9.50: …`) باید در خروجی دیده شود. **عدد کل دقیق نیست** (درس مستند v0.9.46)؛
حدوداً `506 ± 13` طبیعی است. اگر `0 failed` نبود یا یک assertion گام ۵۰ غایب بود →
خروجی کامل را برگردان و توقف.

## مرحله ۳ — publish و ریلیز

```powershell
cd ..\ams-shell\src\Ams.UI
dotnet publish -c Release -r win-x64 --self-contained false
```

زیپ ریلیز: `Classroom-Studio-v0.9.50-release.zip` (همان ۱۵ فایل + `caterina\` و `tools\`).
**قبل از ارسال** تأیید کن:

1. `ClassroomStudio.dll` → **FileVersion = 0.9.50.0** (درس ریلیز جعلی v0.9.39).
2. ریلیز شامل `bridge.py` (هش `e72530b2…`)، `caterina\Caterina.hex` و `tools\isp_flash.py`
   باشد و **هیچ فایل `.cs`/`.xaml` نداشته باشد**.

ریلیز + `test-output-v0.9.50.txt` را برگردان.

## مشخصات بسته

- sha256 زیپ سورس: در پیام همراه ثبت شده است.
- بنر مورد انتظار در لاگ اپ: `Classroom Studio v0.9.50 — board preparation built in …`
