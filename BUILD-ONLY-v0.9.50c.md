# BUILD-ONLY v0.9.50c — فقط build / test / publish (بدون هیچ تصمیم کدنویسی)

این بسته **سورس کامل v0.9.50c** است — v0.9.50 با **سه هات‌فیکس بیلد** (50a: XAML ·
50b: ToggleButton · 50c: usingهای سه سرویس). کار تو فقط سه مرحله است. **هیچ فایلی را
ویرایش نکن، هیچ باگی را «فیکس» نکن.** اگر چیزی شکست خورد، متن کامل خطا را برگردان و توقف کن.

## چه چیزی نسبت به v0.9.50 عوض شده (فقط برای اطلاع — دست‌کاری نکن)

- **پنج فایل سورس:**
  1. `Views/BoardPrepWindow.xaml` (50a) — `TextWrapping` از روی RadioButton به TextBlock
     داخل Content منتقل شد (MC3072).
  2. `Views/BoardPrepWindow.xaml.cs` (50b) — پارامتر `ShowPanel` به
     `System.Windows.Controls.Primitives.ToggleButton` fully-qualified شد (CS0246).
  3. `Services/BoardHexService.cs` (50c) ← `using System; System.IO; System.Linq;`
  4. `Services/BoardsTxtService.cs` (50c) ← `using System; System.Collections.Generic; System.IO; System.Linq;`
  5. `Services/BoardCheckupService.cs` (50c) ← همان‌ها + `System.Threading;`
- علت 50c: روی ماشین بیلد، `System.IO` به‌صورت implicit در دسترس نیست (قرارداد پروژه:
  using صریح — هر ۸ فایل قدیمی همین‌طورند). جزئیات در `docs/board-prep-xaml-hotfix-v0.9.50a.md`.
- شماره‌ی نسخه عمداً **همان `0.9.50`** است؛ بنر و csproj دست‌نخورده.
- `bridge.py` دست‌نخورده (sha256 باید همان `e72530b2…` بماند).

## مرحله ۱ — جایگزینی کامل درخت

قانون طلایی ۱: **هرگز selective merge نه.** درخت قبلی را کامل پاک کن و از زیپ دوباره بساز.

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

**ملاک پذیرش:** خط آخر `0 failed` + هر **۱۷** خط PASS ِ گام ۵۰ (`v0.9.50: …`) حاضر باشد.
**عدد کل دقیق نیست** (درس v0.9.46)؛ حدوداً `506 ± 13` طبیعی است. در غیر این صورت خروجی
کامل را برگردان و توقف.

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
