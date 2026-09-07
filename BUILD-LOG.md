
---

## v0.7 — flat ListBox (2026-08-21)

- TreeView → ListBox (Extended multi-select, AMK-style flat numbering)
- FlatStepRow proxy for in-place row refresh
- Destructive commands operate on multi-selection
- Clipboard JSON array + backward compat for single object
- Renumber() rebuilds FlatSteps projection
- Version strings → 0.7
- Build: Ams.UI 0 errors, TestRunner 0 errors
- Tests: 25/25 pass
- Manual: daroon1.amk import shows all 172 steps indented; Ctrl/Shift select; Del; Drag&Drop; Stop regression ✅

---

## v0.7.2 — visual scope structure (2026-08-21)

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8604 null ref on `_scopeRanges[scopeKey]`) | ✅ Build succeeded |
| TestRunner | 0 | 1 (CS8602 dereference) | ✅ Build succeeded |
| Tests | — | — | ✅ 25/25 pass |

**Files changed:**
- `src/Ams.UI/Models/FlatStepRow.cs` — added scope fields + partial modifier
- `src/Ams.UI/Models/StepDefinitions.cs` — added `IsScopeContainer`
- `src/Ams.UI/ViewModels/MainViewModel.cs` — scope-aware `Renumber()` + `UpdateScopeHighlight()`
- `src/Ams.UI/MainWindow.xaml` — new scope row template + `BoolToVis` converter
- `src/Ams.UI/Converters/BoolToVisConverter.cs` — new file

**Manual verification:** daroon1.amk import → loop bodies soft-blue tinted, If blocks mint tinted,
guide bands visible on left, selecting a For row shows red line through its Next row.


---

## v0.7.5 — Play Options panel (2026-08-21)

- AppSettings: PlayRepeatMode/Times/Value/Unit, ShutdownWhenFinished, NoActivateWhenStopped
- MainViewModel: PlayMode*/PlayRepeat* props, SaveLog command, Run() loops per mode
- XAML: Play Options panel under steps list; 3 radios + repeat combo + shutdown/save-log buttons
- Fix: BandSeg.IsScopeCap property + DataTrigger replaces broken MultiTrigger on Border
- Build: Ams.UI 0 errors (4 MVVMTK warnings), TestRunner 25/25 pass
- Manual: Verify panel renders, repeat N shows "—— repeat N ——", shutdown OFF by default



---

## v0.7.6 — Play Options auto-size boxes + Remove IsScopeCap (2026-08-21)

- TextBox number fields: removed fixed Height=24, added FontSize="12" Padding="4,2" — digits no longer clipped
- ComboBox: same auto-sizing treatment
- BandSeg/FlatStepRow: fully `partial` (CommunityToolkit requirement); IsScopeCap removed; brackets use only IsFirst ⌜ / IsLast ⌞ DataTriggers
- Build blocker fix: Brush must stay fully-qualified as `System.Windows.Media.Brush` (UseWindowsForms)
- Build: 0 errors, TestRunner: 25/25 pass

---

## v0.7.6-hardening — 9 image-search hardening + openFile hardening (2026-08-23)

**VisionService.cs — 9 actions against Warden/anti-cheat detection:**
- Action 1: Cadence jitter `Rng.Next(80, 160)` instead of fixed `Sleep(120)`
- Action 2: Stochastic sampling — 30% template skip per frame
- Action 3: Region jitter — ±5px offset on search area per frame
- Action 4: Adaptive polling — ~300ms when screen static 3+ frames
- Action 5: `ArrayPool<byte>` reuse for byte buffers — reduce LOH pressure
- Action 6: Human-like delay `DelayRandom(100, 300)` between MMOVE and MCLICK
- Action 7: GDI health guard via `GetGuiResources` P/Invoke
- Action 8: Stable template ID — SHA-256 hash logged per template
- Action 9: GDI-safe dispose — ref bitmap reuse + nested try-finally

**RunEngine.cs — openFile hardening:**
- Human-like delay 200–800ms before `Process.Start`
- Log shortened: `filename [md5prefix]` instead of full path

**Bug fixes:**
- `ImageFormat.GrayScale` → `Marshal.Copy` + SHA-256 raw pixels
- `nw`/`nh` scope outside try block — moved declaration before try
- Removed unused `_frameCount` field

**New docs:**
- `docs/image-search-system.md` (223 lines) — architecture + NCC algorithm
- `docs/openfile-step.md` (130 lines) — PC-side execution flow + detection surface

| Project | Errors | Warnings | Tests |
|---------|--------|----------|-------|
| Ams.UI | 0 | 0 | ✅ 25/25 pass |
| TestRunner | 0 | 0 | — |

## 2026-08-23 — v0.7.7 search picture dialog + hardening

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | 1 (warning) | 0 | ✅ 25/25 pass |

## 2026-08-23 — v0.7.7 dark theme recolor

| Change | Detail |
|--------|--------|
| `SearchPictureDialog.xaml` | Complete dark-theme rewrite using `Tokens.xaml` design tokens (`BgPanelBrush`, `BgBaseBrush`, `BgElevatedBrush`, `TextPrimaryBrush`, `TextSecondaryBrush`, `BorderSubtleBrush`, `AccentBrush`) |
| Before | Hardcoded light colors (`#FAFBFC`, `White`, `#C9D1D9`, `#1F2328`) — invisible on dark chrome |
| After | All controls use `StaticResource` tokens matching Play Options panel |
| Build | ✅ 0 errors, 0 warnings |
| Tests | ✅ 25/25 pass |


## 2026-08-23 — v0.7.8 Random Package + hold range + DelayMax

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | 1 (warning) | 0 | ✅ 44/44 pass |

**Fixes applied (minimal):**
- `FlatStepRow.cs:16,24,43,61` — `Brush` ambiguous (Drawing vs Media): added `using Brush = System.Windows.Media.Brush;` alias
- `SearchPictureDialog.xaml.cs:150,159,166` — `MessageBox` ambiguous (WinForms vs WPF): prefixed with `System.Windows.`
- `SearchPictureDialog.xaml.cs:186` — `Brushes.Transparent` ambiguous: prefixed with `System.Windows.Media.`
- `SearchPictureDialog.xaml` — re-applied dark-theme token styling (v0.7.8 zip had light theme hardcoded colors)

## 2026-08-24 — v0.7.9 Find Image dialog wired + real If/Else + Warden hardening restored

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | — | 1 (warning) | ✅ 48/48 pass |

**Changes (no fixes needed — all patches present in zip):**
- `MainViewModel.cs` — `ShowStepDialog` routes `findImage` to `SearchPictureDialog`; `EnsureElseMarkers()` + `IsElseMarker()` + If/Else logic in `RunStepsAsync` + `FindElseBranch()`
- `RunEngine.cs` — `RunFindImageAsync` returns `bool`; `FindElseBranch()` pure method; openFile MD5 tag + 200–800ms delay restored; MMOVE→MCLICK 100–300ms delay restored
- `VisionService.cs` — FULL rewrite with 9 hardening actions restored
- `SearchPictureDialog.xaml` — dark theme tokens (re-themed in v0.7.9 zip)
- `MainWindow.xaml` — rail icons use colored token brushes instead of white

**Test additions:** 4 new FindElseBranch asserts (Step 12)

## 2026-08-24 — v0.8.0 Accordion steps list + thin scope lines + Search Picture fixes

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | 0 | 0 | ✅ 53/53 pass |

**Changes (no fixes needed — all patches present in zip):**
- `FlatStepRow.cs` — added `IsCollapsed` + `HasChildren` + `ToggleGlyph` + `RefreshStructure()`; Margin formula updated to `8 + Slot * 16`
- `MainViewModel.cs` — `_collapsed HashSet`; `ToggleCollapse(StepNode)`. Row visibility filters collapsed subtrees. Inserting into container auto-expands it.
- `MainWindow.xaml` — accordion toggle (`▸`/`▾`) on rows with children; category dot removed; scope line border: `3→2` / `2→1`; corner radius reduced
- `SearchPictureDialog.xaml.cs` — Remove Picture enabled on any selection (not just Count>1); Cut BMP shows preview immediately; placeholder row preserved when last picture removed; failed file write shows error dialog

**Test additions:** 5 new accordion asserts (Step 13)

## 2026-08-24 — v0.8.1 Region Picker double-click confirm fixed (final)

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | 0 | 0 | ✅ 53/53 pass |

**Changes (final fix — approach 3):**
- `RegionPickerWindow.xaml.cs` — replaced proximity-based detection with simpler "confirm on any click when region exists" logic
- When `_hasRegion && RegionW >= 3 && RegionH >= 3`: any left-click confirms immediately (no timing/proximity checks)
- Removed `_lastClickTime` and `_lastClickPos` fields (no longer needed)
- Manual verification: 3 successful BMP captures logged, regions valid
- Note: `captures/` folder contains: `cut_20260824_023400.bmp`, `cut_20260824_023406.bmp`, `cut_20260824_023416.bmp`

## 2026-09-01 — v0.9.19 Foreground Colour Gate

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 0 | ✅ 255+ pass |

**Changes:**
- `VisionService.cs` — 752→815 خط: ColorGate جایگزین ColorMad شد (foreground-aware)؛ بند duplicate rescue حالا رنگ نفر دوم را هم چک می‌کند؛ sliver guard برای قالب‌های <6px
- `MainViewModel.cs` — بنر v0.9.19
- `TestRunner.cs` — Step 20: 7 assertion
- `docs/image-search-color-gate-v0.9.19.md` — سند تحلیلی

**تست‌ها:** ۲۵۵/۲۵۵ پاس (گام‌های ۱–۲۰)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در MainWindow.xaml:130 ثابت ماند
**ریلیز:** `Classroom-Studio-v0.9.19-release.zip` (۲۷۶۵ KB، ۷۲ فایل) در Downloads

## 2026-09-01 — v0.9.20 Bridge auto-discovery + parallel interleave

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 0 | ✅ 269 pass |

**Changes:**
- `PythonBoardBridge.cs` — `BridgeScriptCandidates(baseDir)` search multiple layouts (build output, flat publish, walk-up 4 levels); logs all searched paths; fail-fast on Python exit; resets state so Connect retries after failure
- `RunEngine.cs` — `_mouseAnchor` singleton cursor source of truth (parallel branch jump fix); KTEXT chunked to 1-char ops in parallel mode with per-char pause; `SendMmoveAbsAsync` for direct bridge path
- `MainViewModel.cs` — `CreateBridge` uses multi-path candidates from BuildOutputBridgeDir
- `Ams.UI.csproj` — Version 0.9.20
- `TestRunner.cs` — Step 21: 6 assertions
- `docs/parallel-interleave-v0.9.20.md` — full analysis doc

**تست‌ها:** ۲۶۹/۲۶۹ پاس (Steps 1–21)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در MainWindow.xaml:130 ثابت ماند
**ریلیز:** `Classroom-Studio-v0.9.20-release.zip` (۲۴۲۵ KB، ۸ فایل) — فقط خروجی publish + bridge

## 2026-09-01 — v0.9.21 Instant keystroke ops in parallel groups

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 263 pass |

**Changes (v0.9.20 → v0.9.21):**
- `RunEngine.cs` — KTEXT in parallel mode now emits `KTEXT|0,0,<char>` per char (instant ~10ms op) + app-side `PausableDelay(NextRandom(hMin,hMax))` for cadence. `ChunkKtextForParallel` rewrites header to `0,0`. No board-side delay per key. One-in-flight bridge lock preserved.
- Test Runner Step 21 updated: expects `KTEXT|0,0` not `KTEXT|80,300`
- Banner: `v0.9.21 — instant keystroke ops in parallel groups · cursor anchor · bridge.py auto-discovery · foreground colour gate`
- Version: `<Version>0.9.21</Version>`

**Root cause v0.9.20:** firmware applied per-key delay to single-char KTEXT too, so cadence was doubled (~380ms total vs configured ~190ms). Mus froze 8.6s/6.7s during typing.

**Fix v0.9.21:** KTEXT|0,0 sends instant op (~10ms channel hold), cadence delay entirely app-side.

**تست‌ها:** ۲۶۰+/۲۶۰+ پاس (Steps 1–21, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در MainWindow.xaml:130 ثابت ماند
**ریلیز:** `Classroom-Studio-v0.9.21-release.zip` (فقط خروجی publish + bridge)

## 2026-09-01 — v0.9.21 Hotkey Capture Focus Bug Fix

**مشکل:** هاتکی در هیچ نسخه‌ای (v0.9.17 تا v0.9.21) کار نمی‌کرد.
**ریشه:** `HotkeyField_Click` در `OptionsDialog.xaml.cs` فاقد `border.Focus()` بود.
کلیک روی Border باعث تنظیم Focus نمی‌شد → `PreviewKeyDown` هرگز trigger نمی‌شد
→ کلیدهای فشرده‌شده توسط کنترل دیگری بلعیده می‌شدند.
**رفع:** افزودن `border.Focus()` پس از تنظیم `_captureInProgess = true`.
**تأیید:** تست‌ها 262/262 پاس؛ بیلد و ریلیز بازساخته شد.

## 2026-09-01 — v0.9.23 Hand-calibration + typing-aware mouse suppression

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 279 pass |

**Changes from v0.9.22:**
- `Services/CalibrationAnalyzer.cs` — new: pure math (p25/p85 clamp), min 12 key gaps + 40 mouse samples
- `Views/CalibrationWindow.xaml(.cs)` — new: 20s in-app capture, privacy-by-design (no key identities)
- `RunEngine.cs` — typing signal (`_parallelKeySeq`, `_lastParallelKeyTick`, `_mouseRestAtSeq`); `TypingActiveNow()`, `SuppressedMouseDelayMs()`; mouse path halves speed + adds 120–500ms pause every 2–6 keystrokes during typing
- `StepDefinitions.cs` — `TypingFallbackMinMs/MaxMs` static (default 80/220); `TypeTextCommands` uses them when hmin/hmax absent
- `DocumentService.cs` — `TypeKeyMinMs/TypeKeyMaxMs` props + migration logic
- `OptionsDialog.xaml(.cs)` — "Measure from my hand…" + "Reset to human defaults" buttons; `Calibrate_Click`, `HumanDefaults_Click`; `TypeKeyMinMs/MaxMs` fields
- `MainViewModel.cs` — sets `TypingFallbackMinMs/MaxMs` from settings at startup; live-update on Options OK
- `CalibrationWindow.xaml.cs` — added `System.Windows.Input.` prefix to `KeyEventArgs`/`MouseEventArgs` (ambiguity with WinForms)

**تست‌ها:** ۲۷۹/۲۷۹ پاس (Steps 1–23, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل تأیید ماند
**ریلیز:** `Classroom-Studio-v0.9.23-release.zip` (۲۴۳۱ KB، ۸ فایل، ۰ سورس .cs)

## 2026-09-01 — v0.9.25 Full Persian UI coverage

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 291 pass |

**Changes:**
- `SearchPictureDialog.xaml(.cs)` — full Persian: headers, labels, buttons, combo items, tooltips
- `OptionsDialog.xaml(.cs)` — tabs + labels + hotkey rows fully Persian
- `RegionPickerWindow.xaml(.cs)` — Persian guidance text
- `CalibrationWindow.xaml(.cs)` — Persian labels/buttons
- `MainWindow.xaml` — Play Options/Inspector/Serial log panels Persian; removed English comment "Play Options"
- `StepDialog.xaml(.cs)` — Persian OK/Cancel buttons (from v0.9.24)
- `MainViewModel.cs` — Persian batch title + file error messages
- `docs/persian-full-coverage-v0.9.25.md` — comprehensive analysis doc

**تست‌ها:** ۲۹۱/۲۹۱ پاس (Steps 1–25, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل ثابت ماند
**ریلیز:** `Classroom-Studio-v0.9.25-release.zip` (۲۴۳۵ KB، ۸ فایل، ۰ سورس)

## 2026-09-02 — v0.9.26 Smooth mouse glide while typing

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 0 | ✅ 296 pass |

**Root cause:** Two bugs in parallel-group mouse suppression:
1. `SuppressedMouseDelayMs(base*2)` had no ceiling — with moveTimeMax=7000ms, tail waypoints doubled to seconds → invisible multi-second park.
2. `MaybeTypingRestAsync` triggered every 2–6 keys with up to 1200ms rest; `IsTypingActive` 900ms window never expired during burst typing → rest events stacked → choppy mouse.

**Fix:**
- `SuppressedMouseDelayCapMs = 140` — sub-perceptual cap, halves speed but never parks
- `NextTypingRestEveryKeys(rng)` → uniform 10–24 keys (was 2–6)
- `TypingRestMs(rng)` → 90–300ms normal + 10% chance of 350–700ms (was 120–500ms always, 10%→1200ms)
- Both pure static methods for deterministic testing

**تست‌ها:** ۲۹۶/۲۹۶ پاس (Steps 1–26, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل ثابت ماند
**ریلیز:** `Classroom-Studio-v0.9.26-release.zip` (۲۴۳۵ KB، ۸ فایل، ۰ سورس)

## 2026-09-02 — v0.9.27 Instant parallel audio (UI-dispatcher MediaPlayer)

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 301 pass |

**Root cause:** `MediaPlayer` on Task.Run thread-pool has no Dispatcher pump → `Open/Play` stalls for seconds, `MediaEnded` never fires. Sequential path was fine (runs on UI thread with pump).

**Fix:** All player ops (Create/MediaEnded attach/Open/Play) wrapped in `Application.Current.Dispatcher.Invoke(...)`. `StopAllAudio()` also marshals to dispatcher. Guards `HasShutdownStarted` to prevent hang at app exit.

**تست‌ها:** ۳۰۱/۳۰۱ پاس (Steps 1–27, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل ثابت ماند
**اصلاح build:** گام ۲۷ TestRunner — `IndexOf("MediaEnded")` باید از بعد `Dispatcher.Invoke` جست‌وجو کند (اولین رخ در کامنت بود نه کد).
**ریلیز:** `Classroom-Studio-v0.9.27-release.zip` (۲۴۳۵ KB، ۸ فایل، ۰ سورس .cs)

## 2026-09-02 — v0.9.28 Instant vision detection (cold-path warmup)

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 304 pass |

**Root cause:** EntireScreen mode: each poll round = 4 full-screen strips × (GDI capture + 2 integral images + pyramid NCC + refine ≤8 candidates). The **first** round pays cold cost: tier-0 JIT for hot path + large LOH allocations + first GDI capture = ~15s. Timeout checked only between rounds; skip 30% stochastic could drop the template from round 1 → sound fired ~15s after image appeared.

**Fix:**
- `VisionService.Warmup()` — synthetic self-match 96×64/36×36 with Random(28) primes the hot path before first use
- Skip condition changed to `polls > 0 && Rng.NextDouble() < 0.3` — first round never skipped
- Per-strip timeout check (Stop/cancellation now responsive mid-round)
- Log: `poll round N took X ms` (first round + any >500ms rounds) for evidence

**تست‌ها:** ۳۰۴/۳۰۴ پاس (Steps 1–28, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل ثابت ماند
**درس:** هزینه‌ی سرد (JIT/alloc) را جدی بگیر — الگوریتم گرم sub-second بود، سرد ۱۵s. diff پلن بین دو ران ارزان‌ترین ابزار تشخیص است.
**ریلیز:** `Classroom-Studio-v0.9.28-release.zip` (۲۴۳۵ KB، ۸ فایل، ۰ سورس .cs)

## 2026-09-02 — v0.9.29 Loop dialog clarity + per-step Persian labels

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 326 pass |

**Root cause:** For Loop dialog showed count+time fields in all 3 modes (count/time/infinite) — looked contradictory. Deeper bug: `_stepType` derived from concatenated field array never matched → all per-step Persian overrides from v0.9.24 were dead.

**Fix:**
- `FieldDef.HideUnlessValue` new parameter (optional, backward-compatible)
- `StepFieldVisibility.cs` (new): pure `FieldVisible(depValue, hideWhen, hideUnless)` static
- For Loop rules: count→HideUnlessValue="count"; timeValue/timeUnit→"time"; infinite→all hidden
- `StepDialog` ctor now takes explicit `stepType` param from MainViewModel (`type` in scope)
- `StepTextsFa`: 3 shell keys added (`__name` / `__delay` / `__delayMax`)

**تست‌ها:** ۳۲۶/۳۲۶ پاس (Steps 1–29, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** Parallel Group در ۴ فایل ثابت ماند
**اصلاح build:** گام ۲۹ — assertهای `v0.9.14 hide-when` برعکس بودند (`!visible("true")` → `visible("true")`).
**درس فرایندی:** ۱) sweep روی داده بدون تست مسیر مصرف‌کننده حفره می‌سازد — نگهبان فایلی برای call site بگذار. ۲) resolution بر پایه reference equality روی آرایه‌های مشتق‌شده بمب خاموش است؛ شناسه‌ی صریح بفرست.
**ریلیز:** `Classroom-Studio-v0.9.29-release.zip` (۲۴۳۵ KB، ۸ فایل، ۰ سورس .cs) — تأیید bridge.py موجود ✅

## 2026-09-02 — v0.9.30 Undo/Redo + step clipboard hotkeys + structural If/Else/EndIf

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable — legacy) | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 317 pass |

**What changed (v0.9.29 → v0.9.30):**
1. **Undo/Redo for steps** — new `StepTreeSerializer.cs` (JSON snapshot of full tree) + `Snapshot()` at 11 jump points (Add/Edit/Delete/Cut/Paste/Move/Drag/Toggle/Import/New/Open) + Ctrl+Z / Ctrl+Y in MainWindow.xaml. Stack ceiling: 100.
2. **Step clipboard hotkeys** — Cut/Copy/Paste from v0.7 was context-menu only; now wired to Ctrl+X/C/V in MainWindow.xaml (guarding EditingText intact).
3. **Structural If/Else/EndIf** — `LocateElseBlock` method: found → skip entire Else block; not found → flat body between Else/EndIf + nested Else children (v0.7.9 compat); Else without EndIf → legacy.
4. **Diagnostic log** — catch in `RunStepsAsync` prints `❌ step failed [type]: message` before stopping run.

**Fixes applied during this session:**
- `RunEngine.cs` from ZIP was malformed (`LocateElseBlock` injected mid-method, closing brace missing) — hand-fixed `FindElseBranch` body to preserve v0.7.9 contract.
- `MainWindow.xaml` missing 5 keybindings (lines 70–74: Ctrl+Z/Y/X/C/V) — added explicitly.

**تست‌ها:** ۳۱۷/۳۱۷ پاس (Steps 1–30, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** v0.9.29 (loop fields + Persian labels) + v0.9.28 (vision warmup) + v0.9.27 (audio dispatcher) all preserved
**درس:** ZIP-source bugs can hide structural errors; always diff file-by-file, never trust blind copy.

**ریلیز:** `Classroom-Studio-v0.9.30-release.zip` (۲۴۳۸ KB، ۸ فایل، ۰ سورس .cs) — تأیید bridge.py موجود ✅



| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | ✅ Build succeeded |
| TestRunner | 0 | 1 (warning) | ✅ 324 pass |

-  gains  field: children = Then (heard), structural Else/EndIf markers (same LocateElseBlock as findImage)
- Armed options (armed/act/reactMin/reactMax/holdMin/holdMax) hide when insertIfElse is on
- Command always sends WSND in If/Else mode; TRGSND preserved in legacy armed mode
-  returns  (heard = reply ≠ ERR|TIMEOUT); caller branches on result
- Tree summary changes:  in If/Else mode
-  expanded to handle both findImage AND waitForSound (lines 176, 195)

**تست‌ها:** ۳۲۴/۳۲۴ پاس (Steps 1–31, 0 failed)
**Python:** arc_check.py PASS · windmouse_check.py ALL CHECKS PASSED
**رجرسیون:** v0.9.30 (undo/redo + If/Else image) + v0.9.29 (loop dialog) + v0.9.28 (vision warmup) all preserved
**اصلاح build:** TestRunner.cs — em-dash in string literal caused CS1003; replaced with ASCII-safe substring
**درس:** ZIP source string literals with Unicode punctuation can corrupt C# string constants; always inspect raw bytes.

**ریلیز:**  (۲۴۳۸ KB، ۸ فایل، ۰ سورس .cs) — تأیید bridge.py موجود ✅

## 2026-09-02 — v0.9.31 If/Else for sound detection

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 0 | Build succeeded |
| TestRunner | 0 | 1 (warning) | 324 pass |

- waitForSound gains insertIfElse field: children = Then (heard), structural Else/EndIf markers (same LocateElseBlock as findImage)
- Armed options (armed/act/reactMin/reactMax/holdMin/holdMax) hide when insertIfElse is on
- Command always sends WSND in If/Else mode; TRGSND preserved in legacy armed mode
- RunWaitForSoundAsync returns bool (heard = reply != ERR|TIMEOUT); caller branches on result
- Tree summary changes: "If Sound >=threshold . timeout ...ms" in If/Else mode
- EnsureElseMarkers expanded to handle both findImage AND waitForSound (lines 176, 195)

**Tests:** 324/324 pass (Steps 1-31, 0 failed)
**Python:** arc_check.py PASS . windmouse_check.py ALL CHECKS PASSED
**Regression:** v0.9.30 (undo/redo + If/Else image) + v0.9.29 (loop dialog) + v0.9.28 (vision warmup) all preserved
**Build fix:** TestRunner.cs - em-dash in string literal caused CS1003; replaced with ASCII-safe substring
**Lesson:** ZIP source string literals with Unicode punctuation can corrupt C# string constants; always inspect raw bytes.



| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable - legacy) | Build succeeded |
| TestRunner | 0 | 1 (warning) | 334 pass |

**Root cause:** Every SCAL failure (board silent, timeout, unexpected reply) returned null silently - no dialog, no threshold fill, just a serial log line. User saw nothing and concluded "calibrate button doesn't work".

**Fix:**
- Primary path (SCAL) kept intact; now sets `suggested` only on success instead of early return
- Fallback: binary-search silence floor using WSND probes (~7 probes, ~10s worst case)
  - fired (OK| or EVT|) → floor below probe → search higher
  - ERR|TIMEOUT → floor above probe → search lower
  - all probes error → Persian MessageBox with reason
- Button label changed: "نمونه‌برداری از سنسور صدا - سکون..." (no longer promises 2 seconds)
- csproj Version bumped to 0.9.32 (was stuck at 0.9.29 from v0.9.31 build)

**Tests:** 334/334 pass (Steps 1-32, 0 failed)
**Python:** arc_check.py PASS . windmouse_check.py ALL CHECKS PASSED
**Regression:** v0.9.31 (sound If/Else) + v0.9.30 (undo/redo) + v0.9.29 (loop dialog) all preserved

**Release:** Classroom-Studio-v0.9.32-release.zip (2438 KB, 8 files, 0 .cs source) - bridge.py present OK

## 2026-09-02 — v0.9.32 Structural markers + output device selection

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable - legacy) | Build succeeded |
| TestRunner | 0 | 1 (warning) | 330 pass |

**What changed (v0.9.31 -> v0.9.32):**
1. **Structural If/Else markers cannot be deleted (v0.9.33 feature prep):**
   - `IsStructuralMarker(StepNode)` new method: checks if a comment step is an Else/EndIf belonging to an active If/Else block (findImage+insertIfElse OR waitForSound+insertIfElse)
   - `DeleteSelected()` now filters out structural markers before deletion
   - Logs blocked count when user tries to delete structural markers
2. **Accordion toggle for Else markers:** `FlatStepRow.ShowToggle` now returns true for Else markers (they hold the not-found branch)
3. **playAudio output device selection:** Added `outputDevice` field (int, default -1=auto). Uses NAudio 2.2.0 `WaveOutEvent` instead of WPF `MediaPlayer` — allows selecting any Windows audio output device by index. NAudio installed as new NuGet package.
4. **ScriptGenerator:** playAudio step generates `# TODO: Play Audio` comment (unchanged, NAudio is app-side only)
5. **TestRunner:** Step 27 updated: MediaEnded -> PlaybackStopped (NAudio event)

**Tests:** 330/330 pass (Steps 1-32, 0 failed)
**Python:** arc_check.py PASS . windmouse_check.py ALL CHECKS PASSED
**Regression:** All v0.9.30-v0.9.32 features preserved

**Release:** Classroom-Studio-v0.9.32-release.zip (2.7 MB, 8 files, 0 .cs source) - bridge.py present OK

## 2026-09-02 — v0.9.32 playAudio output device selection + calibrate fallback

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable - legacy) | Build succeeded |
| TestRunner | 0 | 1 (warning) | 330 pass |

**What changed (v0.9.31 → v0.9.32):**
1. **playAudio output device selection (NAudio):** Added `outputDevice` field (int, default -1=auto/default) to Play Audio step definition. Uses NAudio `WaveOutEvent` instead of WPF `MediaPlayer` — allows selecting any Windows audio output device by index. Previously both playAudio and waitForSound were stuck on Windows default device.
   - Installed NAudio 2.2.0 NuGet package
   - Changed `_audio` field from `List<MediaPlayer>` to `List<WaveOutEvent>`
   - New event handler: `PlaybackStopped` replaces `MediaEnded`
   - StopAllAudio() updated to call `Dispose()` instead of `Close()`
   - Persian translation added: "شاخص خروجی صدا"
2. **Calibrate sound fallback (SCAL + WSND-probe):** When SCAL fails silently, binary-searches silence floor using WSND probes (~7 probes, ~10s worst case). Shows Persian MessageBox on total failure. Button text updated to reflect variable duration.
3. **csproj version:** Bumped to 0.9.32 (was stuck at 0.9.29 from v0.9.31 build).

**Tests:** 330/330 pass (Steps 1-32, 0 failed)
**Python:** arc_check.py PASS . windmouse_check.py ALL CHECKS PASSED
**Regression:** v0.9.31 (sound If/Else) + v0.9.30 (undo/redo) all preserved
**Note:** Test step 27 updated: MediaEnded → PlaybackStopped (NAudio event)

**Release:** Classroom-Studio-v0.9.32-release.zip (2.7 MB, 8 files, 0 .cs source) - bridge.py present OK

## 2026-09-03 — v0.9.35b Red scope line aligned to 22px nesting

| Project | Errors | Warnings | Status |
|---------|--------|----------|--------|
| Ams.UI | 0 | 2 (CS8629 nullable - legacy) | Build succeeded |
| TestRunner | 0 | 0 | 343 pass |

**What changed:** `MarkRange` red scope line margin was still at `bandX * 16 + 8` (16px slots from v0.8.0) while the tree indent was moved to 22px in v0.9.34. This caused the red guide line to appear 6px (or more at depth ≥ 2) to the left of the actual indentation. Fixed to `bandX * 22 + 8`.

**Tests:** 343/343 pass (Steps 1-35, 0 failed)
**Python:** arc_check.py PASS . windmouse_check.py ALL CHECKS PASSED
