# AMS WPF Shell — Session Changelog (۲۰۲۶-08-21)

**تاریخ:** ۲۰۲۶-08-21
**نسخه:** v0.6.1 + v0.6.2
**پروژه:** `C:\Users\wasteland\Documents\ams-wpf-shell-v0.6`

---

## خلاصه

- رفع باگ مرگبار قفل لوله (pipe deadlock) در `AmkImporter.cs` و `TestRunner.cs` —
  decoder خروجی ~۱۲ کیلوبایت متنی فارسی به stdout می‌فرستد، C# فقط stderr می‌خواند،
  بافر لوله پر می‌شود و فرآیند پایتون گیر می‌کند.
- رفع باگ قفل دکمه Run در v0.6.2 — event `aborted` در `PythonBoardBridge.cs` هندل نمی‌شد
  و `SendAsync` تا timeout منتظر می‌ماند.
- v0.6.2: پشتیبانی از abort فوری از طریق `bridge.py` v2 (worker thread + HALT آنی).

---

## تغییرات فایل‌ها

### 1. `ams-shell/src/Ams.UI/Services/AmkImporter.cs` (v0.6.1 — رفع pipe deadlock)

**خط 60–82:** اضافه شدن encoding UTF-8 و خواندن هم‌زمان stdout/stderr

```diff
+ using System.Text;   // ← اضافه شد

  var psi = new ProcessStartInfo("python")
  {
+     RedirectStandardOutput = true,
+     StandardOutputEncoding = Encoding.UTF8,
      RedirectStandardError = true,
+     StandardErrorEncoding = Encoding.UTF8,
      UseShellExecute = false,
      CreateNoWindow = true,
  };
  // ...
  var p = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start python.");
+ // Read stdout + stderr concurrently to avoid pipe-buffer deadlock:
+ // the decoder emits ~12 KB of Persian text to stdout which would fill
+ // the OS pipe (≈4 KB) and block the child if nobody reads it.
+ using var tOut = new CancellationTokenSource(65_000);
+ using var tErr = new CancellationTokenSource(65_000);
+ var outTask = p.StandardOutput.ReadToEndAsync().WaitAsync(tOut.Token);
+ var errTask = p.StandardError.ReadToEndAsync().WaitAsync(tErr.Token);
  p.WaitForExit(60_000);
+ string stdout = outTask.IsCompletedSuccessfully ? outTask.Result : "";
+ string stderr = errTask.IsCompletedSuccessfully ? errTask.Result : "";
  if (p.ExitCode != 0 || !File.Exists(jsonFile))
-     throw new InvalidOperationException("amk_decoder failed (exit " + p.ExitCode + "): " + p.StandardError.ReadToEnd().Trim());
+     throw new InvalidOperationException("amk_decoder failed (exit " + p.ExitCode + "): " + stderr.Trim());
```

---

### 2. `tests/TestRunner.cs` (v0.6.1 — رفع pipe deadlock در تست‌ها)

**خط 129–134:** import test — تبدیل به Task.Run با timeout 60 ثانیه

```diff
- var result = await AmkImporter.Import(...);
+ var importTask = Task.Run(() =>
+     AmkImporter.Import(
+         @"C:\Users\wasteland\Documents\ams\pc\daroon1.amk",
+         @"C:\Users\wasteland\Documents\ams\pc"));
+ var result = importTask.Wait(TimeSpan.FromSeconds(60)) ? importTask.Result : null;
```

**خط 217–237:** PNG extraction test — اضافه کردن UTF-8 encoding و خواندن هم‌زمان

```diff
  var psi = new ProcessStartInfo("python",
      $"\"C:/Users/wasteland/Documents/ams/pc/amk_decoder.py\" " +
      $"\"C:/Users/wasteland/Documents/ams/pc/daroon1.amk\" " +
      $"--json \"{Path.Combine(Path.GetTempPath(), "decoded_test.json")}\" " +
      $"--imgdir \"{imgDir}\"")
  {
      UseShellExecute = false,
      RedirectStandardError = true,
+     RedirectStandardOutput = true,
+     StandardOutputEncoding = System.Text.Encoding.UTF8,
+     StandardErrorEncoding = System.Text.Encoding.UTF8,
      CreateNoWindow = true,
      EnvironmentVariables = { ["PYTHONIOENCODING"] = "utf-8" }
  };
  using var p = Process.Start(psi);
+ // Read both streams concurrently to avoid pipe-buffer deadlock
  var outTask = p.StandardOutput.ReadToEndAsync();
  var errTask = p.StandardError.ReadToEndAsync();
  p.WaitForExit(30000);
  outTask.Wait(); errTask.Wait();
```

**خط 172–173:** Else branch assertion — رفع CS1513 (null-conditional chaining)

```diff
- if (n.Name == "Else branch" || n.Props.GetValueOrDefault("text")?.Contains("Else") == true)
+ var t = n.Props.GetValueOrDefault("text") as string;
+ if (n.Name == "Else branch" || (t != null && t.Contains("Else")))
```

---

### 3. `ams-shell/src/Ams.UI/Services/PythonBoardBridge.cs` (v0.6.2 — fix aborted handling)

**خط 215–222:** افزودن مورد `aborted` به HandleLine

```diff
  case "reply":
      _replyTcs?.TrySetResult(root.GetProperty("reply").GetString() ?? string.Empty);
      break;

+ case "aborted":
+     // Board-side abort (HALT sent by bridge.py on {"op":"abort"}).
+     // Bridge sets abort_flag BEFORE writing HALT, so the reply we
+     // get here is already the board's response to the abort.
+     // Resolve the pending SendAsync so the caller unblocks immediately
+     // instead of waiting on the full command window.
+     _replyTcs?.TrySetResult(root.GetProperty("reply").GetString() ?? "");
+     break;
+
  case "disconnected":
      SetState(BridgeState.Disconnected);
      break;
```

---

### 4. `ams-shell/src/Ams.UI/Services/RunEngine.cs` (v0.6.2 — abort غیرمرمیر)

**خط 291–299:** `ERR|...|aborted` مانند `ERR|TIMEOUT` رفتار می‌کند

```diff
  if (reply.StartsWith("ERR|", StringComparison.Ordinal))
  {
-     // a sound window expiring is a normal outcome, not a fatal error (§3.3.1 group E)
-     if (allowTimeout && reply.StartsWith("ERR|TIMEOUT", StringComparison.Ordinal))
+     // a sound window expiring or aborted is a normal outcome, not a fatal error
+     // (§3.3.1 group E / v0.6.2 abort)
+     if (allowTimeout && (reply.StartsWith("ERR|TIMEOUT", StringComparison.Ordinal)
+                      || reply.Contains("|aborted", StringComparison.OrdinalIgnoreCase)))
      {
-         _log("sound window expired (timeout) — continuing");
+         _log("command aborted/timed out — continuing");
          return reply;
      }
      throw new InvalidOperationException($"Board replied {reply} to {cmd}");
  }
```

---

## تغییرات v0.6.2 (بدون اصلاح — فقط استخراج از zip)

| فایل | وضعیت |
|------|-------|
| `bridge/bridge.py` | v2 با worker thread + abort op (از zip) |
| `IBoardBridge.cs` | متد `SendAbortAsync()` اضافه شد (از zip) |
| `PythonBoardBridge.cs` | پیاده‌سازی `SendAbortAsync()` + **رفع bug aborted** (این نشست) |
| `MainViewModel.cs` | `Stop()` → `SendAbortAsync()` + settle HALT (از zip) |
| `DocumentService.cs` | بدون تغییر عملکردی (از zip) |

---

## دستورالعمل تست

```bash
# Build
taskkill /F /IM Ams.UI.exe 2>/dev/null
cd ams-shell/src/Ams.UI && dotnet build

# TestRunner
cd ../../../../tests && dotnet run --no-build

# Manual abort test (نیاز به برد فیزیکی)
cd ../src/Ams.UI && dotnet run
# Connect(AUTO) → For loop(count=3) → Wait for Sound(threshold=90, timeout=20s)
# Right-click → Run → بعد ~2 ثانیه Stop (Shift+F2)
# Expected: log "aborting the in-flight board command (instant)"
#           "ERR|WSND|aborted"
#           Run button re-enables within ~1s
```

---

## نتیجه تست‌ها

```
=== Results: 25 passed, 0 failed ===
Import: 58 top-level steps (≥50) ✅
PNG extraction: 9 images ✅
Build: 0 errors, 0 warnings ✅
```

---

## یادداشت‌های فنی

- `aborted` event از bridge.py فقط وقتی emit می‌شود که `abort_flag.is_set()` باشد — یعنی
  کاربر Stop را زده باشد. در این حالت reply از برد حاوی `ERR|...|aborted` است.
- `SendAbortAsync()` fire-and-forget است و قفل `_ioLock` را دور می‌زند — این عمدی است
  (abort نباید پشت فرمان در حال اجرا صف بکشد).
- `Stop()` در MainViewModel اول `SendAbortAsync()` می‌فرستد، سپس 800ms صبر می‌کند
  و `HALT` backup می‌فرستد تا state برد پاک شود.

---

## v0.7 — flat AMK-style ListBox (TreeView → ListBox)

### تغییرات
- **TreeView → ListBox** در `MainWindow.xaml`: `SelectionMode="Extended"` برای انتخاب چندتایی ویندوزی (Ctrl toggle / Shift range).
- فایل جدید `Models/FlatStepRow.cs`: proxy روی `StepNode` — PropertyChanged را forward می‌کند تا ردیف بدون rebuild آپدیت شود.
- `MainViewModel.cs`:
  - `FlatSteps` collection (ObservableCollection\<FlatStepRow\>) — projection pre-order tree.
  - `SelectedNodes` (List\<StepNode\>) — توسط view در SelectionChanged ست می‌شود.
  - `EffectiveSelection()` — selected nodes را topmost-only می‌کند (descendantهای ancestor حذف می‌شوند).
  - `Delete/Cut/Copy/ToggleDisabled/BatchDelays` روی کل selection عمل می‌کنند.
  - clipboard: JSON array `[...]` (جدید) + single object (سازگاری معکوس).
  - `Renumber()`: FlatSteps را با reuse ردیف‌های قدیمی reprojects می‌کند.
  - version string → `v0.7`.
- `DocumentService.cs`: version → `0.7`.
- Event handlers: `StepsTree_*` → `StepsList_*`؛ drag-drop adapted برای ListBox.

### نتیجه
- Import daroon1.amk: تمام ۱۷۲ node visible و indented (پیش‌تر nodes داخلی flat دیده می‌شدند).
- Ctrl+click / Shift+click / Delete / Cut / Copy / Paste روی multi-select کار می‌کند.
- Drag & drop: before/after/into روی ردیف‌های ListBox.
- Stop regression: instant abort → Run button re-enables within ~1s.
- ۲۵/۲۵ تست واحد پاس.

### فایل‌های تغییرکرده
- `ams-shell/src/Ams.UI/MainWindow.xaml`
- `ams-shell/src/Ams.UI/MainWindow.xaml.cs`
- `ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs`
- `ams-shell/src/Ams.UI/Services/DocumentService.cs`
- `ams-shell/src/Ams.UI/Models/FlatStepRow.cs` (جدید)


---

## v0.7.2 — visual scope structure (2026-08-21)

- `FlatStepRow`: new ctor `(node, number, depth, scopeKey, scopeTint, scopeBand)`;
  `[ObservableProperty]` fields for scope head/tail border state; convenience props
  `ScopeBandVis`, `HeadLineVis`, `HeadLineBrush`, `TailLineVis`, `TailLineBrush`
- `StepDefinitions`: `IsScopeContainer` on `forLoop` + `findImage`
- `MainViewModel.Renumber()`: walks with `Stack<(node,key,headIndex)>`; consumes
  marker siblings (Next / Else / End If comment rows); records `scopeRanges` per key
- `UpdateScopeHighlight()`: sets IsScopeHead/IsScopeTail per row
- `MainWindow.xaml`: new row template — tint border, left guide-band border,
  head/tail red-line Borders, `BoolToVis` converter resource
- Build: Ams.UI 0 errors, TestRunner 0 errors · Tests: 25/25 pass

---

## v0.7.2 — visual scope structure (refined, 2026-08-21)

- Replaced initial implementation with user-provided zip reference
- `FlatStepRow`: `ScopeKey` is `StepNode?` (node ref not string); `RowBg` + `Bands` (VSCode-style indent guides); `[ObservableProperty]` on `_inSelectedScope`, `_inSelectedScopeSoft`, `_redLineMargin`
- `MainViewModel.Renumber()`: `WalkList` recursive walk; `AddRow` helper; `TintFor`/`BandsFor` static helpers; scope range keyed by `StepNode`
- `UpdateScopeHighlight()`: triggered via `OnSelectedNodeChanged` partial void hook; strong line for container's own range, soft line for every enclosing scope
- `BoolToVisConverter` removed — WPF's built-in `BooleanToVisibilityConverter` used instead
- Scope palette: 3-tier pastel blue for loops, 3-tier mint for If/Else blocks
- Build: Ams.UI 0 errors, TestRunner 0 errors · Tests: 25/25 pass

---

## v0.7.3 — full src replacement (2026-08-21)

- Full src replacement from user-provided zip (do NOT merge selectively)
- `StepNode.Children`: `set` added (v0.7.1 fix retained) — enables `File → Open` JSON deserialization
- `DocumentService.version` → `"0.7.3"`
- Startup log → `"AMS shell v0.7.3 — consolidated full tree · Open keeps the whole tree …"`
- `FlatStepRow`: fixed `partial` + fully-qualified `Brush` (same two build-blockers as v0.7.2)
- Build: Ams.UI 0 errors, TestRunner 0 errors · Tests: 25/25 pass

---

## v0.7.4 — scope BRACKETS + rail redesign (2026-08-21)

- `FlatStepRow.Bands`: now `IReadOnlyList<BandSeg>` (each BandSeg has `IsFirst`/`IsLast` bracket caps)
- New `BandSeg` class: `ObservableObject` with `Color`, `Slot`, `Margin` (4 + slot*10px), `IsFirst`/`IsLast`
- `Renumber()` post-pass sets bracket caps on first/last rows per scope
- Red scope line: `IsScopeHead`/`IsScopeTail` (+Soft variants) for ⌜/⌞ brackets
- Left rail: `RailButton` style with emoji icons + captions; 7 colored icon buttons
- XAML fix: replaced broken `MultiTrigger` (Condition on Border) with `DataTrigger` using `RelativeSource Self` + Tag check
- Build fixes from zip: `partial` on `BandSeg` + `FlatStepRow`, fully qualified `Brush`
- Version → `0.7.4`; startup log updated
- Build: Ams.UI 0 errors, TestRunner 0 errors · Tests: 25/25 pass
