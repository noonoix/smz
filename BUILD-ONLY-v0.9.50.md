# BUILD-ONLY v0.9.50 — فقط build / test / publish (بدون هیچ تصمیم کدنویسی)

این بسته **سورس کامل v0.9.50** است (مبنا: v0.9.49، sha256 زیپ در انتهای همین فایل).
کار تو فقط سه مرحله است. **هیچ فایلی را ویرایش نکن، هیچ باگی را «فیکس» نکن، هیچ پیشنهاد
کدی اجرا نکن.** اگر چیزی شکست خورد، متن کامل خطا را برگردان و توقف کن.

## چه چیزی تازه است (فقط برای اطلاع — دست‌کاری نکن)

- پنجره‌ی تازه‌ی «آماده‌سازی برد» (Tools → Board Preparation) + سه سرویس تازه در
  `Services/Board*.cs` + `Views/BoardPrepWindow.*`.
- **یک پکیج NuGet تازه: `System.IO.Ports` 8.0.0** — `dotnet build` خودش restore می‌کند؛
  همان ماشینی که CommunityToolkit.Mvvm / NAudio / WPF-UI را restore می‌کرد. اگر restore
  به‌خاطر شبکه شکست خورد، یک بار `dotnet restore` را جدا اجرا کن و دوباره build بگیر.
- دو فایل همراه به خروجی کپی می‌شوند (مثل bridge.py): `caterina\Caterina.hex` و
  `tools\isp_flash.py` — در publish باید دیده شوند.
- `bridge.py` دست‌نخورده است (sha256 باید همان `e72530b2…` بماند).

## مرحله ۱ — جایگزینی کامل درخت

قانون طلایی ۱: **هرگز selective merge نه.** محتوای زیپ را روی یک پوشه‌ی تمیز extract کن
(یا درخت قبلی را کامل پاک کن و از زیپ دوباره بساز).

## مرحله ۲ — build و تست

```powershell
cd ams-shell
dotnet build -c Release
```

انتظار: **۰ خطا**. (دو warning شناخته‌شده‌ی `CS8629` روی VisionService.cs از قبل هستند و
دست نمی‌خورند.)

```powershell
cd ..\tests
dotnet run 2>&1 | Tee-Object test-output-v0.9.50.txt
```

**ملاک پذیرش (قاعده‌ی جدید پروژه):** خط آخر باید `0 failed` بگوید و هر **۱۷** خط PASS ِ
گام ۵۰ (`v0.9.50: …`) باید در خروجی دیده شود. **عدد کل دقیق نیست** چون یک sweep تصادفی با
خروج زودهنگام در TestRunner هست (درس مستند v0.9.46)؛ حدوداً `506 ± 13` طبیعی است.
اگر `0 failed` نبود یا یکی از ۱۷ assertion گام ۵۰ غایب بود → خروجی کامل را برگردان و توقف.

## مرحله ۳ — publish و ریلیز

```powershell
cd ..\ams-shell\src\Ams.UI
dotnet publish -c Release -r win-x64 --self-contained false
```

از خروجی publish، زیپ `Classroom-Studio-v0.9.50-release.zip` بساز (همان ۱۵ فایل همیشگی
+ دو پوشه‌ی تازه‌ی `caterina\` و `tools\`) و **قبل از ارسال** این دو را تأیید کن:

1. `ClassroomStudio.dll` → Properties → **FileVersion = 0.9.50.0** (درس ریلیز جعلی v0.9.39).
2. ریلیز باید شامل `bridge.py` (هش `e72530b2…`)، `caterina\Caterina.hex` و
   `tools\isp_flash.py` باشد و **هیچ فایل `.cs`/`.xaml` نداشته باشد**.

ریلیز + `test-output-v0.9.50.txt` را برگردان.

## مشخصات بسته

- sha256 زیپ سورس: در پیام همراه ثبت شده است.
- بنر مورد انتظار در لاگ اپ: `Classroom Studio v0.9.50 — board preparation built in …`
