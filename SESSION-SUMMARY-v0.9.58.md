=== BUILD-ONLY v0.9.58 Summary ===

**Date:** 2026-09-05

**Build:** 680 passed, 3 failed

**3 Remaining Failures:**
1. v0.9.45: the loop vein closes on its visible Next row — needs assertion update for OwnsNextMarker migration
2. v0.9.47: Next is still the loop's own sibling closing row — same cause
3. v0.9.56: BundleVersion is 0.9.58 — version pin assertion

**Key Files Modified:**
- Ams.UI.csproj: bridge\** wildcard bundling
- bridge/bridge.py: detect_board_port brain-first probe
- Services/PicoFirmwareExporter.cs: keypad BTN1/GP2 + BTN2/GP3
- Services/GlobalHotkeyService.cs: VK_NUMLOCK(0x90) + VK_SCROLL(0x91) always registered
- ViewModels/MainViewModel.cs: IsScopeMarker uses OwnsNextMarker
- Tests/TestRunner.cs: all version pins → 0.9.58, Step 58 added

**Known Bug:** BoardPrepWindow.xaml.cs line 802 had foreach var e causing CS0136 — fixed by renaming to foreach var fam

**Release Artifacts:**
- Classroom-Studio-v0.9.58-release.zip (C:/Users/wasteland/Downloads/)
- test-output-v0.9.58.txt
- build-v0.9.58.txt

**v0.9.57 was previously implemented:**
- PortablePaths.cs (FirstExistingDir, FirstExistingFile, FindPython)
- bridge/ams_serial.py, ams_crypto.py, serial/ vendored
- bridge.py: sys.path.insert(0, dirname), stage events, 0x2E8A PID
- DocumentService.cs: sanitize stale PythonDir/ToolkitDir/Port
- PythonBoardBridge.cs: PortablePaths.FindPython(), 15s Connect timeout
