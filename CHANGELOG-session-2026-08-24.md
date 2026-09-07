# CHANGELOG — ۲۰۲۶-08-24

**پروژه:** `ams-wpf-shell-v0.6`
**نسخه‌ها:** v0.8.2 + v0.8.3

---

## خلاصه روز

۱. **v0.8.2** — View BMP Position: فیکس HitInsideApp post-filter برای وقتی اپ >95٪ صفحه رو پوشش می‌ده
۲. **v0.8.3** — دو گام جدید: playAudio (wav/mp3) + runExe (Process.Start) + دکمه Browse…
۳. **v0.8.3** — تلطیف متن Else marker از "Else branch — runs when…" به "Else" ساده
۴. **v0.8.3** — Summary فیلد findImage با If-Else → پیشوند "If" (مثلاً "If Find image · 75% …")
۵. تست‌ها: ۵۶/۵۶ پاس

---

## v0.8.2 — View BMP Position: HitInsideApp Post-Filter

### مشکل
وقتی اپلیکیشن بیش از 95٪ صفحه رو پوشش می‌ده (مثلاً maximized روی 1936×1048 از 1920×1080):
- نوارهای `ComputeSearchRegions` بیش‌ازحد باریک می‌شن (top=0px, left=0px, right=0px, bottom=40px)
- تصاویر داخل خود UI اپ گاهی match می‌شن و موس به نقطهٔ اشتباه می‌ره
- نتیجه: **View BMP Position تصویر داخل برنامه رو پیدا می‌کنه نه تصویر روی دسکتاپ**

### راه‌حل
اضافه شدن post-filter `HitInsideApp()` در حلقهٔ hit detection:
```csharp
if (appClipped && HitInsideApp(result.Value.p, appB.Value)) continue;
```
هر هیتی که نقطه‌اش داخل bounds پنجرهٔ اپ باشه → reject می‌شه، فارغ از اینکه stripها چقدر تنبل بودن.

### تست‌ها
- ✅ 56/56 unit tests pass
- ✅ Build: 0 errors
- ✅ Manual test: View BMP Position → تصویر خارج از اپ

### فایل تغییرکرده
- `ams-shell/src/Ams.UI/Services/VisionService.cs` — `HitInsideApp()` + post-filter در `FindOnScreen`

---

## v0.8.3 — playAudio + runExe Steps + Browse Button

### ویژگی‌های جدید

#### ۱. playAudio — پخش audio (wav/mp3)
- Fields: `path` (فایل audio), `loop` (bool, repeat until stopped)
- Color: `StepAudioBrush` (#FFB158FF purple)
- Icon rail: 🔈 Audio
- Non-blocking: fire-and-forget برای non-loop; engine ادامه می‌ده
- Loop: MediaPlayer زنده می‌مونه، MediaEnded → Play دوباره

#### ۲. runExe — اجرای اجرایی
- Fields: `path`, `args` (optional), `windowState` (normal/minimized/maximized)
- Color: `StepPackageBrush` (pink)
- Icon rail: 🚀 Run
- Human-like launch delay: 200–800ms (همان openFile)
- Process.Start با UseShellExecute=true

#### ۳. دکمه Browse… برای فیلدهای path
- `FieldDef` ← پارامتر اختیاری `BrowseFilter`
- `StepDialog.BuildForm()` → دکمهٔ "Browse…" زیر هر فیلد path
- Uses `System.Windows.Controls.Button` (نه Wpf.Ui) برای visible بودن روی پس‌زمینهٔ تیره
- اعمال‌شده به: `openFile.path`, `playAudio.path`, `runExe.path`, `playScript.path`
- Filterها:
  - playAudio → "Audio files|*.wav;*.mp3|All files|*.*"
  - runExe → "Executables|*.exe|All files|*.*"
  - openFile/playScript → "All files|*.*" / "AMS scripts|*.amk|All files|*.*"

#### ۴. تلطیف Else marker
- متن قدیم: `"Else branch — runs when the picture is NOT found"`
- متن جدید: `"Else"`
- findImage با insertIfElse=true → summary: **"If Find image · …"** (پیشوند "If")
- `EnsureElseMarkers` بعد از import هم صدا زده می‌شه (قبلاً فقط موقع add/edit)

### تست‌ها
✅ 56/56 pass

| تست | توضیح |
|------|-------|
| playAudio definition exists | color/fields/summarize |
| runExe definition exists | color/fields/summarize |
| Browse button renders | FieldDef.BrowseFilter → button in dialog |
| Else marker text | `"Else"` نه متن طولانی |
| ifSummaryWithIfElse | `"If Find image · …"` |
| imported AMK Else recognized | `"Else — …"` prefix still works |

### فایل‌های تغییرکرده
- `ams-shell/src/Ams.UI/Models/StepDefinitions.cs` — playAudio + runExe defs + BrowseFilter param
- `ams-shell/src/Ams.UI/Views/StepDialog.xaml.cs` — Browse button rendering + OnBrowseClick handler
- `ams-shell/src/Ams.UI/Services/RunEngine.cs` — case "playAudio" + case "runExe"
- `ams-shell/src/Ams.UI/Resources/Tokens.xaml` — StepAudioColor + StepAudioBrush
- `ams-shell/src/Ams.UI/MainWindow.xaml` — rail buttons + menu items
- `ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs` — EnsureElseMarkers بعد از import + Else text
- `tests/TestRunner.cs` — elseComments check updated to StartsWith("Else")

### الگوی استفاده با findImage
```
findImage (insertIfElse = true)
  ├── ✅ Then branch
  │     ├── playAudio (found.wav)          ← notify on detection
  │     └── runExe (C:\apps\bot.exe)      ← trigger external app
  └── ❌ Else branch
        └── playAudio (timeout.wav)        ← alert on timeout
```

---

## v0.8.3 — Insert Label + Go To Label

### ویژگی‌های جدید

#### ۱. `label` — درج برچسب
- Fields: `label` (متن ساده، پیش‌فرض `"label1"`)
- Color: `StepFlowBrush` (همان رنگ جریان)
- Summary: `🏷 label_name`
- عملکرد: inert — هیچ دستوری به بورد نمی‌فرستد (break بدون command)
- در ScriptGenerator: `# ==== label: X ====`

#### ۲. `gotoLabel` — پرش به برچسب
- Fields: `label` (EditableCombo — لیبل‌های موجود در scope)
- Color: `StepFlowBrush`
- Summary: `Go To Label → label_name`
- مکانیزم: throw `GotoSignal(label)` → unwind تا `RunAsync` → `FindLabelRow(list, label)` → `si = targetRow`
- Jump forward: steps بین goto و label skip می‌شوند
- Cross-level escape: از درون loop به label سطح بالا می‌پرد
- Unresolved label: warning logged, script stops cleanly (no crash)
- در ScriptGenerator: `# TODO: Go To Label 'X' — run via the AMS app`

#### ۳. `FieldKind.EditableCombo` — کمبو با تایپ دستی
- `StepDialog.BuildForm()`: `IsEditable = true` + current value kept visible even if not in options
- `Ok_Click`: `.Text.Trim()` for editable combo (not `.SelectedItem`)
- `MainViewModel.ShowStepDialog`: قبل از ساخت dialog، لیبل‌های موجود را جمع‌آوری و در options می‌گذارد

#### ۴. منوی جدید
- Insert menu: `Insert Label` + `Go To Label` (after playScript)
- Context menu Add Action: دو آیتم مشابه + Separator بعدی

### تست‌ها
✅ 64/64 pass (۸ تست جدید برای label/gotoLabel اضافه شد)

| تست | توضیح |
|------|-------|
| label definition exists | color/fields/summarize |
| gotoLabel definition exists | color/fields/summarize |
| label summary shows name | `?? start` |
| FindLabelRow case-insensitive | `LABEL` matches `label` |
| FindLabelRow returns -1 | missing label |
| goto jumps forward | skips intermediate steps |
| cross-level escape | loop → root-level label |
| unresolved goto | warning + clean stop, no crash |

### فایل‌های تغییرکرده
- `ams-shell/src/Ams.UI/Models/StepDefinitions.cs` — `EditableCombo` enum + label + gotoLabel defs
- `ams-shell/src/Ams.UI/Services/RunEngine.cs` — `GotoSignal`, `FindLabelRow`, while-loop (si manual), case "label"/"gotoLabel"
- `ams-shell/src/Ams.UI/Views/StepDialog.xaml.cs` — EditableCombo rendering + Ok_Click trim
- `ams-shell/src/Ams.UI/MainWindow.xaml` — Insert menu + context menu items
- `ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs` — CollectLabels before dialog + `.ToArray()` on def.Fields
- `ams-shell/src/Ams.UI/Services/ScriptGenerator.cs` — comment output for label/gotoLabel
- `tests/TestRunner.cs` — ۸ تست جدید مرحله ۱۵

### bug fix
- `def.Fields = def.Fields` → `def.Fields.ToArray()` (خطای CS0266 — تبدیل IReadOnlyList→FieldDef[])
- تست `Defs` private → استفاده از `StepDefinitions.Get()` public

### الگوی استفاده
```
findImage (insertIfElse = true)
  ├── ✅ Then branch
  │     ├── label ("check_done")        ← نقطهٔ بازگشت
  │     └── runExe (reset_app.exe)
  └── ❌ Else branch
        └── gotoLabel ("check_done")    ← پرش به label، رد شدن از intermediates
```

---

## Random Reboot During Play (Mini-Feature)

### ویژگی
- چک‌باکس «Random reboot during play» در Play Options
- دو فیلد عددی: `min` و `max` دقیقه
- وقتی Play زده شود و چک‌باکس روشن باشد:
  - یک `Task.Delay` با تاخیر تصادفی بین min و max شروع می‌شود
  - اگر اسکریپت قبل از موعد تمام شود → تایمر لغو می‌شود
  - اگر تایمر سررسید برسد → `shutdown /r /t 0` اجرا می‌شود
- ذخیره در `ams-settings.json` (همانند ShutdownWhenFinished)

### تست‌ها
✅ 64/64 pass (تست جدیدی اضافه نشد — این قابلیت runtime است)

### فایل‌های تغییرکرده
- `DocumentService.cs` — `RandomRebootEnabled`, `RandomRebootMin`, `RandomRebootMax`
- `MainViewModel.cs` — Properties + منطق در `RunAsync`
- `MainWindow.xaml` — چک‌باکس + دو فیلد عددی

---

## نتایج نهایی Build & Test

| پروژه | Errors | Warnings | Tests |
|-------|--------|----------|-------|
| Ams.UI | 0 | 0 | ✅ |
| TestRunner | 0 | 0 | ✅ 64/64 pass |

---

### خلاصه تغییرات به‌صورت نسخه‌ای

| نسخه | تاریخ | ویژگی‌های کلیدی | تست‌ها |
|------|-------|-----------------|--------|
| v0.8.2 | ۲۰۲۶-08-24 | HitInsideApp post-filter → View BMP Position خارج از اپ | 56/56 |
| v0.8.3 (پیش) | ۲۰۲۶-08-24 | playAudio + runExe + Browse button + Else "Else" + If prefix | 56/56 |
| v0.8.3 (نهایی) | ۲۰۲۶-08-24 | Insert Label + Go To Label + EditableCombo | 64/64 |

---

### نکات مهم

- `GotoSignal` یک custom exception است که unwind را از هر depth‌ای مدیریت می‌کند (هم‌چون `goto` در C)
- حلقهٔ `for` به `while` تبدیل شد تا `si` دستی تنظیم شود
- `FieldKind.EditableCombo`: برای comboboxهایی که کاربر باید مقدار دلخواه هم تایپ کند (مثل label names)
- لیبل‌ها case-insensitive جستجو می‌شوند (` StringComparison.OrdinalIgnoreCase`)
- `FindLabelRow` فقط siblings هم‌سطح (یا level بالاتر در cross-level) را جستجو می‌کند، children را نه
- `def.Fields.ToArray()` ضروری است چون `StepDefinition.Fields` readonly record property است

---

*تولید شده توسط Claude Code — ۲۰۲۶-08-24*
