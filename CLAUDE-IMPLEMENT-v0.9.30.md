# پرامپت build — Classroom Studio v0.9.30

فایل `Classroom-Studio-v0.9.30.zip` را استخراج کن و به‌عنوان درخت کامل پروژه جایگزین کن.

## قانون طلایی

**هرگز selective merge نکن** — کل `ams-shell/src/` و `tests/TestRunner.cs` و `docs/` کامل جایگزین شوند. فایل جدید `Models/StepTreeSerializer.cs` در درخت هست (csproj با globbing نیازی به ویرایش ندارد).

## چه چیزی عوض شده (v0.9.29 → v0.9.30)

۱) **Undo/Redo برای استپ‌ها** — وجود نداشت؛ حالا اسنپ‌شات JSON تمام‌درخت (`StepTreeSerializer`) + `Snapshot()` در ۱۱ نقطه‌ی جهش (Add/Edit/Delete/Cut/Paste/Move/Drag/Toggle/Import/New/Open) + Ctrl+Z / Ctrl+Y. سقف پشته ۱۰۰.
۲) **هاتکی‌های کلیپ‌برد استپ** — Cut/Copy/Paste از v0.7 بود ولی فقط منوی راست‌کلیک؛ Ctrl+X/Ctrl+C/Ctrl+V در MainWindow.xaml وصل شد (نگهبان EditingText سالم).
۳) **If/Else/EndIf ساختاری** — قبلاً «End If» نقش نداشت و استپ‌های flat بین نشانگرها همیشه اجرا می‌شدند؛ حالا `LocateElseBlock`: found → فقط Then و رد شدن کل بلوک Else; not found → بدنه‌ی flat بین Else/EndIf + فرزندهای تو‌در‌توی Else (سازگاری v0.7.9); Else بدون End If → legacy.
۴) **لاگ تشخیصی** — catch کلی RunStepsAsync چاپ می‌کند `❌ step failed [type]: message` قبل از توقف run (برای باگ «بسته‌شدن بلافاصله‌ی» 3.amsj — خط لاگ را در گزارش بیاور).

## بلوک build

```powershell
cd ams-shell
Get-Process ClassroomStudio -ErrorAction SilentlyContinue | Stop-Process -Force
dotnet clean AMS.sln -c Release
dotnet build AMS.sln -c Release
dotnet run --project ..\tests\TestRunner.csproj | Tee-Object -FilePath ..\test-output-v0.9.30.txt
python tests\windmouse_check.py
```

## معیارهای پذیرش

- [ ] build بدون error و بدون warning جدید
- [ ] TestRunner — گام‌های ۱ تا ۳۰ همه PASS (گام ۳۰ = ۸ assertion جدید)
- [ ] بنر: `Classroom Studio v0.9.30 — undo/redo + step clipboard hotkeys …`
- [ ] منوی Insert شامل Parallel Group است
- [ ] فایل `test-output-v0.9.30.txt` همراه گزارش برگردد

## تست دستی

۱. Undo/Redo: افزودن/حذف/جابه‌جایی چند استپ → Ctrl+Z چندبار → Ctrl+Y; Ctrl+X/C/V روی استپ‌ها; داخل تکست‌باکس دیالوگ Ctrl+V الصاق متن بماند.
۲. If/Else flat: استپ واقعی بین «Else»/«End If» — پیدا شد → اجرا نشود; پیدا نشد → اجرا شود.
۳. پلن 3.amsj: اجرا و **ارسال خطوط لاگ از Run تا توقف** (مخصوصاً `❌ step failed […]`). توجه: Play Options روی «تکرار به مدت ۱ minute» بود — سقف بیرونی ۱ دقیقه.
۴. پلن 2.amsj (عدد `poll round 1`) و pj6 (صفر فریز ≥۵۰۰ms) سالم بمانند.

## publish

```powershell
dotnet publish src\Ams.UI\Ams.UI.csproj -c Release -o ..\artifacts\publish-v0.9.30
```

تأیید حیاتی: `bridge\bridge.py` در خروجی باشد + صفر فایل `.cs` در ریلیز.
