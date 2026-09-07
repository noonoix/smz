# v0.9.30 — Undo/Redo for Steps + Structural If/Else/EndIf

## خلاصه تغییرات

### ۱) Undo/Redo برای استپ‌ها (اولین بار)

- `StepTreeSerializer.cs` (جدید در `Models/`): دو متد استاتیک
  - `Snapshot(List<StepNode> tree)` → string JSON کل درخت
  - `Restore(string json)` → List<StepNode> با Parent rewire
- `MainViewModel.cs`:
  - پشته ۱۰۰ تایی `_snapshotStack` / `_redoStack`
  - متد `Snapshot()` قبل از هر تغییر سازه‌ای صدا زده می‌شود
  - `Undo()` / `Redo()` commands
  - ۱۱ نقطه‌ی جهش: Add/Edit/Delete/Cut/Paste/Move/Drag/Toggle/Import/New/Open
- `MainWindow.xaml`: ۵ keybinding جدید
  ```xml
  <KeyBinding Key="Z" Modifiers="Control" Command="{Binding UndoCommand}" />
  <KeyBinding Key="Y" Modifiers="Control" Command="{Binding RedoCommand}" />
  <KeyBinding Key="X" Modifiers="Control" Command="{Binding CutCommand}" />
  <KeyBinding Key="C" Modifiers="Control" Command="{Binding CopyCommand}" />
  <KeyBinding Key="V" Modifiers="Control" Command="{Binding PasteCommand}" />
  ```

### ۲) هاتکی‌های کلیپ‌برد استپ

- از v0.7: Cut/Copy/Paste فقط در منوی راست‌کلیک
- v0.9.30: Ctrl+X/C/V در MainWindow.xaml وصل شد
- نگهبان: `EditingText` سالم می‌ماند (وقتی textbox در فوکوس است، hotkey اثر نمی‌کند)

### ۳) If/Else/EndIf ساختاری

**مشکل v0.9.29:** «End If» نقش نداشت؛ استپ‌های flat بین نشانگرها همیشه اجرا می‌شدند.

**راه‌حل:** `LocateElseBlock` در `RunEngine.cs`:
- `found` → Only Then runs (children of If) + skip entire Else block
- `not found` → flat body between Else/EndIf + nested Else children (v0.7.9 compat)
- `Else without EndIf` → legacy behavior (non-structural, safe fallback)

**بازسازی:** `FindElseBranch` (v0.7.9) + `LocateElseBlock` (v0.9.30) هر دو static public در RunEngine.

**تست‌ها (گام ۳۰):** ۸ assertion
1. Snapshot round-trip structure and props
2. Restore rewires [JsonIgnore] Parent links
3. Flat Else…End If block located around real step body
4. No markers → no structural block
5. Else without EndIf stays non-structural (safe legacy)
6. Else after non-comment sibling is not the If's branch (v0.7.9 contract)
7. Undo/redo snapshot infrastructure present in ViewModel
8. Ctrl+Z/Ctrl+V keybindings wired in MainWindow

### ۴) لاگ تشخیصی

- catch کلی در `RunStepsAsync`: `❌ step failed [type]: message` قبل از توقف run
- هدف: رفع باگ «بسته‌شدن بلافاصله‌ی 3.amsj» — خط لاگ در گزارش بیاور

## اصلاحات session

- ZIP منبع خراب بود: `LocateElseBlock` وسط بدنه‌ی `FindElseBranch` درج شده، closing brace缺失
- `RunEngine.cs` دستی فیکس شد
- `MainWindow.xaml` ۵ keybinding خط ۷۰-۷۴ اضافه شد

## تست‌ها

- **۳۱۷/۳۱۷ پاس** (Steps 1–30, 0 failed)
- **arc_check.py**: PASS
- **windmouse_check.py**: ALL CHECKS PASSED
- **رجرسیون**: v0.9.29 (loop fields + Persian labels) + v0.9.28 (vision warmup) + v0.9.27 (audio dispatcher) همه preserved

## ریلیز

- `Classroom-Studio-v0.9.30-release.zip` (۲۴۳۸ KB، ۸ فایل، ۰ سورس .cs)
- مسیر: `C:\Users\wasteland\Downloads\`

## درس فرایندی

۱) ZIP-source bugs can hide structural errors — always diff file-by-file, never trust blind copy.
۲) TestRunner با V27ReadSrc از مسیر نسبی می‌خواند؛ هر تغییر XAML باید keybindingها را هم cover کند.
