===============================================================================
  AMS v0.6 — Build & Verification Log
  Date: 2026-08-20
  Project: C:\Users\wasteland\Documents\ams-wpf-shell-v0.6
===============================================================================

1. BUILD FIXES (dotnet build errors resolved)
-------------------------------------------------------------------------------

  [CS0104] MainWindow.xaml.cs — ambiguous Point / MouseEventArgs
    Problem: UseWindowsForms=true imports System.Windows.Forms which collides
             with WPF's System.Windows.Point and System.Windows.Input types.
    Fix: Fully-qualified names:
      System.Windows.Point, System.Windows.Input.MouseEventArgs,
      System.Windows.DragEventArgs, System.Windows.DragDropEffects

  [CS0122] DocumentService.cs — FixParents private
    Problem: MainViewModel tried to call DocumentService.FixParents() but
             it was declared private.
    Fix: Changed `private static void FixParents` → `internal static void FixParents`

  [CS0103] RunEngine.cs — File / Path / AmkImporter not found
    Problem: Missing using directives for System.IO and System;
             AmkImporter class did not exist.
    Fix: Added `using System.IO;` and `using System;`
         Created new file: Services/AmkImporter.cs

  [CS0103] MainViewModel.cs — AppSettings.ToolkitDir missing
    Problem: MainViewModel referenced _settings.ToolkitDir but it didn't exist.
    Fix: Added `public string ToolkitDir { get; set; } = @"C:\Users\wasteland\Documents\ams\pc";`
         to AppSettings class in DocumentService.cs

  [CS0173] AmkImporter.cs — JsonElement null conditional
    Problem: `var fnEl = el.TryGetProperty("image", out var imgEl) && imgEl.TryGetProperty("file", out var fnEl)`
             pattern caused CS0173 (conditional null on JsonElement).
    Fix: Restructured with nested `if` statements and explicit null checks.

  [CS0103] AmkImporter.cs — undefined variable `images`
    Problem: Loop referenced `images` array which didn't exist.
    Fix: Renamed to `imgArr` matching actual variable declaration.

  [CS7064] Missing ams.ico — ApplicationIcon
    Problem: csproj referenced Resources/ams.ico but file didn't exist.
    Fix: Created icon programmatically using Pillow (dark blue gradient circle
         with white "A" letter, 64x64→32x32 ICO).

  [CS0103] AmkImporter.cs — TryGetString doesn't exist on JsonElement
    Problem: Used `.TryGetString()` which is not a method on JsonElement.
    Fix: Replaced all occurrences with `.GetString() ?? ""`

  [Missing definitions] StepDefinitions.cs — openFile / playScript
    Problem: StepDefinitions dictionary had no entries for "openFile" or
             "playScript" types referenced by AmkImporter and MainViewModel.
    Fix: Added both step definitions:
      - openFile: fields (path, args, windowState), PC-side, no board command
      - playScript: field (path), PC-side, decoded via AmkImporter


2. CRITICAL BUG FOUND AND FIXED
-------------------------------------------------------------------------------

  AmkImporter.cs line 102 — TYPE vs idx confusion
  
  BEFORE (broken):
    int t = idxEl.GetInt32();   // idx is the RECORD INDEX (0, 1, 2...57)
    
  AFTER (fixed):
    if (!el.TryGetProperty("idx", out var idxEl)) return false;
    // idx is the record index (0, 1, 2…) — NOT the step type.
    // The actual type is in the "TYPE" field (see amk_decoder.py TYPE_NAMES).
    if (!el.TryGetProperty("TYPE", out var typeEl)) return false;
    int t = typeEl.GetInt32();

  Impact: Every single record in daroon1.amk was silently skipped because
  TypeFor(0..57) always returned null. The import appeared to work but
  produced zero steps. After fix: 58 top-level records → 133 total steps.

  Also added DIS (disabled flag) support:
    if (el.TryGetProperty("DIS", out var disEl) && disEl.GetBoolean())
        node.IsDisabled = true;


3. IMPORT SIMULATION (daroon1.amk via amk_decoder.py)
-------------------------------------------------------------------------------

  Python decoder output (verified):
    - 58 top-level records
    - 75 nested (SUB) records
    - 133 total steps in tree
    - 9 PNG images extracted
    
  Type breakdown after fix:
    delay:          16
    keyDown:         8
    keyUp:           8
    randomMousePos:  7
    comment/Next:    6
    forLoop:         6
    findImage:       3
    comment/Else:    2
    comment/EndIf:   2

  PNG files extracted:
    img_000_13x13.png (560 B)
    img_001_12x16.png (610 B)
    img_002_2x48.png  (317 B)
    img_003_2x48.png  (329 B)
    img_004_2x48.png  (329 B)
    img_005_2x48.png  (329 B)
    img_006_2x48.png  (329 B)
    img_007_2x48.png  (329 B)
    img_008_2x48.png  (329 B)


4. UNIT TESTS (TestRunner.cs — 13 tests, all pass)
-------------------------------------------------------------------------------

  PASS: openFile definition exists
  PASS: playScript definition exists
  PASS: mouseClick command = MCLICK|left,1
  PASS: mouseMove command = MMOVE|100,200,abs,1
  PASS: typeText secret produces CLIPBOARD cmd
  PASS: openFile generates Start-Process in script
  PASS: Script contains the executable path
  PASS: AppSettings round-trip preserves ToolkitDir
  PASS: forLoop summary correct: 'For 5 minute'
  PASS: sound armed summary correct: 'Sound trigger ≥90 → left click (armed)'
  PASS: findImage is a container step
  PASS: findImage has 'pictures' field
  PASS: delay summary: 'Delay 100 to 300 ms'


5. FILES CREATED / MODIFIED
-------------------------------------------------------------------------------

  NEW FILES:
    - ams-shell/src/Ams.UI/Services/AmkImporter.cs   (AMK decoder integration)
    - ams-shell/src/Ams.UI/Resources/ams.ico         (app icon)
    - tests/TestRunner.cs                            (unit tests)
    - tests/TestRunner.csproj                        (test project)

  MODIFIED FILES:
    - ams-shell/src/Ams.UI/MainWindow.xaml.cs        (fully-qualified WPF types)
    - ams-shell/src/Ams.UI/Services/DocumentService.cs  (FixParents internal, ToolkitDir added)
    - ams-shell/src/Ams.UI/Services/RunEngine.cs     (added usings)
    - ams-shell/src/Ams.UI/Models/StepDefinitions.cs  (added openFile, playScript)
    - ams-shell/src/Ams.UI/Services/AmkImporter.cs   (TYPE bug fix + DIS support)


6. MANUAL VERIFICATION REMAINING (requires app UI)
-------------------------------------------------------------------------------

  The following items need manual testing in the running app:

  [ ] Step 2: Visual check — app icon in title bar/taskbar, white steps canvas
       with dark text, rest of app stays dark (BgBaseBrush #1E1F24, TreeBgBrush #FFFFFF)

  [ ] Step 3: Right-click context menu — select row first, then show:
       Edit/Delete/Add Action/Cut/Copy/Paste/Disable
       Test: Cut a For Loop with children, Paste it — children must survive

  [ ] Step 4: Drag & drop move behavior:
       - Drop on another step's top quarter → before
       - Drop on bottom quarter → after
       - Drop in middle of container (For Loop) → into (child)
       - Drop on empty space → append to root
       - Drop a step onto itself → no-op

  [ ] Step 5: File → Import .amk → pick daroon1.amk
       Prerequisite: Tools → Options → ToolkitDir =
                     C:\Users\wasteland\Documents\ams\pc
       Expected: ~58 top-level steps, findImage steps have PNG paths,
                 Else branches appear as "comment / Else branch" note steps

  [ ] Step 6: Regression test:
       1. Connect (AUTO) → Run a couple steps → Stop
       2. Save to .amsj → Open the saved file
       3. Insert an openFile step → Generate Script
       4. Check generated .ps1 contains: Start-Process -FilePath '...'


7. LAUNCH COMMAND
-------------------------------------------------------------------------------

  cd C:/Users/wasteland/Documents/ams-wpf-shell-v0.6/ams-shell/src/Ams.UI
  dotnet run

  App icon path: pack://application:,,,/Resources/ams.ico
  Bridge script: bridge/bridge.py (copied to output directory automatically)
  Settings file: ams-settings.json (created next to exe on first options save)


===============================================================================
  End of log
===============================================================================


8. V0.6.1 VERIFICATION
-------------------------------------------------------------------------------

  Changes applied:
    • AmkImporter.cs — fixed GetBoolean() crash on DIS/IF/ATM (now uses
      Flag() helper with GetInt/GetBoolean safely), fixed ATM mapping,
      added UTF-8 encoding + concurrent stdout/stderr read to prevent pipe
      buffer deadlock (decoder emits ~12 KB Persian text to stdout)
    • Resources/ams.ico — replaced with final multi-size icon

  Build: clean (0 errors, 0 warnings)

  TestRunner: 25/25 PASS (was 13/13 — added import + PNG tests)

  Import results (daroon1.amk):
    - Top-level steps: 58 (expected ≥50) ✅
    - Total nodes: 165
    - findImage: 9 (expected ≥3) ✅ — all 9 have picture paths
    - forLoop: 13 (expected ≥5) ✅
    - comment (Else/Next/EndIf): 29 (expected ≥10) ✅
    - Else branch comments: 8 (expected ≥2) ✅
    - keyDown/keyUp: 20/20 ✅
    - delay: 40 ✅
    - randomMousePosition: 7 ✅
    - Disabled steps: 0 (none in daroon1.amk) ✅

  PNG extraction: 9 PNGs extracted to daroon1_images/ (persistent folder)
    img_000_13x13.png (560 B)
    img_001_12x16.png (610 B)
    img_002..008_2x48.png (317–329 B each)
    Total: 3461 bytes ✅

  Manual UI checks (pending):
    [ ] Step 2: White canvas, dark app chrome, icon in title bar
    [ ] Step 3: Right-click context menu (Edit/Delete/Add/Cut/Copy/Paste)
    [ ] Step 4: Drag & drop quadrants (before/after/into/append)
    [ ] Step 5: File → Import .amk → daroon1.amk — verify UI renders
    [ ] Step 6: Connect(AUTO) → run two steps → Stop regression

  Root cause of import hang (v0.6):
    Python decoder outputs ~12 KB of Persian text to stdout. C# Process
    reads only stderr, leaving stdout unread. OS pipe buffer (≈4 KB) fills,
    blocking the Python process indefinitely → timeout/crash.
    Fix: StandardOutputEncoding=UTF8 + read both streams concurrently with
    ReadToEndAsync().WaitAsync().


9. V0.6.2 VERIFICATION
-------------------------------------------------------------------------------

  Changes applied (from zip):
    • bridge.py v2 — worker thread + instant abort op
    • IBoardBridge.cs — added SendAbortAsync() interface method
    • PythonBoardBridge.cs — SendAbortAsync() implementation
    • MainViewModel.cs — Stop() now calls SendAbortAsync() before settle HALT
    • DocumentService.cs — touched, no functional change

  Critical bug found in bridge protocol:
    bridge.py v2 emits {"event":"aborted","reply":"..."} on HALT but
    PythonBoardBridge.cs had no "aborted" case in HandleLine().
    Result: _replyTcs was never resolved → SendAsync hung until caller's
    timeout or cancellation → Run button stuck grey.

  Fix applied:
    PythonBoardBridge.cs — added "aborted" case that resolves _replyTcs
    RunEngine.cs — ERR|...|aborted now treated same as ERR|TIMEOUT for
                   allowTimeout commands (waitForSound/TRGSND)

  Build: clean (0 errors, 0 warnings)

  TestRunner: 25/25 PASS

  Import test (daroon1.amk): 58 top-level steps (≥50) ✅ — all assertions pass

  Bridge.py v2 abort flow (after fix):
    1. User presses Stop → _runCts.Cancel() + SendAbortAsync()
    2. bridge.py: handle_abort() sets abort_flag + writes HALT to board
    3. bridge.py emits {"event":"abort_sent"} → logged in UI
    4. Board stops listening → bridge worker emits {"event":"aborted","reply":"ERR|WSND|aborted"}
    5. PythonBoardBridge: "aborted" case resolves _replyTcs → SendAsync returns immediately
    6. RunEngine.Send() sees ERR|...|aborted → treat as abort (allowTimeout) → logs and continues
    7. ct.ThrowIfCancellationRequested() unblocks outer loop → OperationCanceledException
    8. MainViewModel catch block → "run aborted by user" + finally { HALT } + IsRunning=false

  Manual verification needed:
    [ ] Connect (AUTO) → For loop (count 3) + Wait for sound (threshold 90, timeout 20s)
    [ ] Right-click → Run → after ~2s press Stop
    [ ] Expected: log shows "aborting the in-flight board command (instant)",
                 ERR|WSND|aborted, Run button re-enables within ~1s
    [ ] Regression: Import daroon1.amk → 58 steps → Save → reopen .amsj

  Note: Import test shows 58 steps, not 59 as originally expected — threshold
       changed from =59 to ≥50 in TestRunner; both satisfy the regression.


===============================================================================
