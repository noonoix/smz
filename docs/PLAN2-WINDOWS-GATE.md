# PLAN2 Windows gate report

- migration: success
- split runtime: success
- bridge: success
- app build: success
- TestRunner: success

- result: === Results: 752 passed, 0 failed ===

## Migration tail
```
PLAN2 parity migration already applied
PLAN2 parity tests already applied
PLAN2 recursive-bundle migration already applied
PLAN2 recursive-bundle tests already applied
PLAN2 split-runtime template migration already applied
PLAN2 split-runtime C# tests already applied
plan_engine.py 24994 c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac
plan_motion.py 14028 9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8
plan_typing.py 3967 1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5
total 42989
wrote ams-shell\src\Ams.UI\Services\PlanExporter.cs (89914 chars)
plan_engine.py 24994 c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac
plan_motion.py 14028 9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8
plan_typing.py 3967 1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5
round trip: all three split modules byte-identical
MAKE OK
SYNC OK: Step 59 now comes from tools/plan_exporter_test_step.cs.inc
```

## Split-runtime tail
```
PASS parity 1 events 11
PASS parity 2 events 13
PASS parity 3 events 10
PASS parity 4 events 7
PASS parity 5 events 21
PASS parity 6 events 9
PASS parity 7 events 10
PASS parity 8 events 826
PASS parity 9 events 9
PASS negative 1 line 2: ELSE outside an IF block
PASS negative 2 line 2: ENDIF without IFSND/IFLUX
PASS negative 3 GOTO 'missing' has no matching LABEL
PASS negative 4 line 2: INCLUDE needs a plain *.txt file name
PASS negative 5 line 2: RPKG counts out of range (1 items)
PASS negative 6 line 2: PGROUP needs at least two branches
PASS exact bundle canonical 1022
PASS exact bundle split 1022
PASS lazy modules loaded on demand
RESULT 18 passed 0 failed
{'plan_engine.py': 24994, 'plan_motion.py': 14028, 'plan_typing.py': 3967}
```

## App build tail
```
  Determining projects to restore...
  Restored D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj (in 4.37 sec).
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\VisionService.cs(134,72): warning CS8629: Nullable value type may be null. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(52,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(72,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\ViewModels\MainViewModel.cs(2569,52): warning CS8620: Argument of type 'string?[]' cannot be used for parameter 'candidates' of type 'IEnumerable<string>' in 'string? PortablePaths.FirstExistingDir(IEnumerable<string> candidates)' due to differences in the nullability of reference types. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\VisionService.cs(134,72): warning CS8629: Nullable value type may be null. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\ViewModels\MainViewModel.cs(2569,52): warning CS8620: Argument of type 'string?[]' cannot be used for parameter 'candidates' of type 'IEnumerable<string>' in 'string? PortablePaths.FirstExistingDir(IEnumerable<string> candidates)' due to differences in the nullability of reference types. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(52,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(72,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
  Ams.UI -> D:\a\smc\smc\ams-shell\src\Ams.UI\bin\Release\net8.0-windows\ClassroomStudio.dll

Build succeeded.

D:\a\smc\smc\ams-shell\src\Ams.UI\Services\VisionService.cs(134,72): warning CS8629: Nullable value type may be null. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(52,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(72,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\ViewModels\MainViewModel.cs(2569,52): warning CS8620: Argument of type 'string?[]' cannot be used for parameter 'candidates' of type 'IEnumerable<string>' in 'string? PortablePaths.FirstExistingDir(IEnumerable<string> candidates)' due to differences in the nullability of reference types. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI_sh44zpbb_wpftmp.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\VisionService.cs(134,72): warning CS8629: Nullable value type may be null. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\ViewModels\MainViewModel.cs(2569,52): warning CS8620: Argument of type 'string?[]' cannot be used for parameter 'candidates' of type 'IEnumerable<string>' in 'string? PortablePaths.FirstExistingDir(IEnumerable<string> candidates)' due to differences in the nullability of reference types. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(52,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
D:\a\smc\smc\ams-shell\src\Ams.UI\Services\PortablePaths.cs(72,13): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\ams-shell\src\Ams.UI\Ams.UI.csproj]
    8 Warning(s)
    0 Error(s)

Time Elapsed 00:00:43.55
```

## Test tail
```
PASS: v0.9.55: board ids are sanitised to lowercase Arduino ids
PASS: v0.9.55: step 2 has the editable board-spec form back (id, name, VID, PIDs, product, maker)
PASS: v0.9.55: editing a board-spec field refreshes the preview, and defaults can be restored
PASS: v0.9.55: the form explains the auto-fill and the application-PID rule in Persian
PASS: v0.9.55: selecting a device fills step 1 and step 2 with that device's defaults
PASS: v0.9.55: the preview, the install and the uninstall all use the edited board specs
PASS: v0.9.55: auto-fill never fights the user's own typing
PASS: v0.9.55: the port scan lists attached ports only, like the reference tool
PASS: v0.9.55: history rows are still available behind the switch
PASS: v0.9.55: the scan log line counts attached ports and hidden history separately
PASS: v0.9.55: the checkup tab has a history switch and re-renders without a new scan
PASS: v0.9.55: version pins for this release (csproj + banner + bundle)
PASS: v0.9.55: all twenty keyboard identities are selectable device modes
PASS: v0.9.55: every keyboard preset keeps its researched VID/PID and stays CDC (class 0x02)
PASS: v0.9.55: selecting a keyboard prefills the board-spec defaults (product + manufacturer)
PASS: v0.9.55: the checkup tab recognises both the bootloader and the application PID
PASS: v0.9.55: no duplicate device-mode keys after the twenty additions
PASS: v0.9.55: the new identity tables are documented in place
PASS: v0.9.55: scrolled panes keep a 14px inset so the scrollbar never sits on the text
PASS: v0.9.55: the hover hint drops below the icon and switches off while its submenu is open
PASS: v0.9.55: the settings tab and all its sections live inside the main window, not a separate one
PASS: v0.9.55: forLoop can be renamed and owns a type icon
PASS: v0.9.55: parallelGroup can be renamed and owns a type icon
PASS: v0.9.55: randomPackage can be renamed and owns a type icon
PASS: v0.9.55: waitForSound can be renamed and owns a type icon
PASS: v0.9.55: waitForLight can be renamed and owns a type icon
PASS: v0.9.55: findImage can be renamed and owns a type icon
PASS: v0.9.55: a renamed head shows icon + custom title and keeps its informative tail
PASS: v0.9.55: the group-title field has a Persian label
PASS: v0.9.55: markers render as bare lowercase next/else while real comments keep the # prefix
PASS: v0.9.55: marker rows reclaim the toggle gutter and sit tighter against the red vein
PASS: v0.9.55: version pins for this release (csproj + banner + bundle)

--- Step 56: v0.9.56 UART GP0/GP1 -> GP16/GP17 ---
PASS: v0.9.56: firmware uses GP16/GP17 for UART arm
PASS: v0.9.56: old GP0/GP1 UART pins are gone from firmware exporter
PASS: v0.9.56: generated header comment mentions GP16 = TX and GP17 = RX
PASS: v0.9.56: BH1750 I2C pins untouched (GP21/GP20)
PASS: v0.9.56: BundleVersion is 0.9.64f
PASS: v0.9.56: exported code.py carries GP16/GP17
PASS: v0.9.56: exported code.py does not contain board.GP0
PASS: v0.9.56: boot.py still enables CDC console+data
PASS: v0.9.56: csproj version is 0.9.65

--- Step 57: v0.9.58 portable/self-contained ---
PASS: v0.9.58: ams_serial.py, ams_crypto.py, and vendored pyserial bundled in bridge/
PASS: v0.9.58: bridge.py puts bundled stack first on sys.path
PASS: v0.9.58: brain-first detect_board_port with Pico VID/PID
PASS: v0.9.58: bridge emits stage events
PASS: v0.9.58: all four stage event names present
PASS: v0.9.58: PortablePaths has FirstExistingDir and FirstExistingFile
PASS: v0.9.58: no hardcoded wasteland path in DocumentService defaults
PASS: v0.9.58: AppSettings.Load sanitizes stale paths
PASS: v0.9.58: CreateBridge prefers bundled bridge dir over settings
PASS: v0.9.58: PythonBoardBridge uses PortablePaths.FindPython()
PASS: v0.9.58: ConnectAsync has 15s timeout
PASS: v0.9.58: csproj version is 0.9.65
PASS: v0.9.58: csproj uses bridge wildcard with CopyToOutputDirectory
PASS: v0.9.58d: Pico exporter converts configured modifier + numpad key
PASS: v0.9.60: fixed keypad on GP4/GP3 emits Num Lock and Scroll Lock
PASS: v0.9.58d: send_path parses semicolon-delimited delays, not individual characters
PASS: v0.9.58d: fixed lock-key registrations and their startup warnings are gone
PASS: v0.9.58d: serial log has selected/all clipboard copy actions
PASS: v0.9.58: meta guard located TestRunner.cs on disk
PASS: v0.9.58: all app version pins match current release 0.9.65 (found: 65)
PASS: v0.9.58: all bundle pins stay on the untouched firmware line 0.9.64b (found: 64)

--- Step 58: v0.9.60 firmware consolidation + transport hardening ---
PASS: v0.9.60: version pins (firmware bundle, csproj, app banner)
PASS: v0.9.60: WLUX/TRGLUX/LCAL answer ERR|NOSENSOR when the BH1750 is unplugged
PASS: v0.9.60: the standalone engine never autoruns on boot (AUTOSTART=False)
PASS: v0.9.60: fixed keypad GP4 = Num Lock start/stop, GP3 = Scroll Lock pause/resume
PASS: v0.9.60: serial RX uses a bounded byte buffer, not string concatenation
PASS: v0.9.60: permanent arm pump + fire-and-ack mouse path
PASS: v0.9.60: keyboard always on the Pico; both legacy envelopes are consumed locally
PASS: v0.9.60: exported code.py is fully baked with the fixed control contract
PASS: v0.9.60: bridge stdio is forced to UTF-8 with an ASCII-safe emit fallback
PASS: v0.9.60: the C# side reads the bridge as UTF-8 too
PASS: v0.9.60: the serial log allows Ctrl/Shift multi-selection for copy-selected
PASS: v0.9.60: stableSec 0.5 becomes 500ms on the wire (got: WLUX|1200,1300,500,20000,0)
PASS: v0.9.60: the row summary shows the fractional stabilize time (got: Wait for light 1200-1300 lux for 0.5s · timeout 20000ms)
PASS: v0.9.60: legacy integer stableSec plans still produce the same wire command
PASS: v0.9.60: the step dialog accepts 0.5 regardless of the Windows display language










--- Step 59: v0.9.65 plan exporter (PLAN|2) ---
PASS: v0.9.65: plan header is PLAN|2 with SCREEN and SPEED from settings
PASS: v0.9.65: randomMousePosition emits the exact golden RMOUSE line
PASS: v0.9.65: per-step delay-after lands after the op
PASS: v0.9.65: emission counts are reported
PASS: v0.9.66: mouseMove emits native PLAN|2 MOVETO
PASS: v0.9.65: the engine's built-in idle default never leaks into a point move
PASS: v0.9.66: human=false emits native non-human MOVETO
PASS: v0.9.65: click line with swap-normalized hold
PASS: v0.9.65: TYPE percent-encoding (% -> %25, | -> %7C, newline -> %0A)
PASS: v0.9.65: word pauses + typing cadence defaults from settings
PASS: v0.9.66: C# parity emits WSND|91,70,8000
PASS: v0.9.66: C# parity emits KEY|combo=162+65
PASS: v0.9.66: C# parity emits KDOWN|160
PASS: v0.9.66: C# parity emits KUP|160
PASS: v0.9.66: C# parity emits WHEEL|-3
PASS: v0.9.66: C# parity emits LABEL|again
PASS: v0.9.66: C# parity emits GOTO|again
PASS: v0.9.66: C# parity emits RAW|PING
PASS: v0.9.66: C# parity emits RPKG|all,1,2
PASS: v0.9.66: C# parity emits PKGITEM
PASS: v0.9.66: C# parity emits ENDPKG
PASS: v0.9.66: C# parity emits PGROUP
PASS: v0.9.66: C# parity emits PARITEM
PASS: v0.9.66: C# parity emits ENDPAR
PASS: v0.9.66: runExe/openFile/playAudio emit Win+R macros
PASS: v0.9.66: findImage blocks explicitly
PASS: v0.9.65: non-ASCII typing blocked with the ASCII rule
PASS: v0.9.65: secret typing blocked (no PC clipboard on the Pico)
PASS: v0.9.65: clipboard mode blocked
PASS: v0.9.66: waitForLight If/Else emits IFLUX/ELSE/ENDIF
PASS: v0.9.66: waitForSound If emits IFSND/ENDIF
PASS: v0.9.65: nested findImage + secret typing are NAMED inside a blocked head (3 errors)
PASS: v0.9.65: stray marker error
PASS: v0.9.65: unknown step type error
PASS: v0.9.65: forLoop emits LOOP|2 ... ENDLOOP
PASS: v0.9.65: the loop head consumes its Next marker
PASS: v0.9.65: forLoop time 5 minute -> LOOPTIME|300
PASS: v0.9.65: infinite loop -> LOOP|0
PASS: v0.9.65: Play Options times-3 wraps the whole body
PASS: v0.9.65: Play Options timed 1 minute -> LOOPTIME|60
PASS: v0.9.65: plain WLIGHT (fractional stableSec becomes ms)
PASS: v0.9.65: armed WLIGHT with key + react
PASS: v0.9.65: disabled steps are counted and skipped; comments become # lines
PASS: v0.9.65: KeyboardBoard=promicro is a documented FLAG, not silent
PASS: v0.9.65: delay step is swap-normalized
PASS: v0.9.65: a container's delay-after lands AFTER its ENDLOOP (app semantics)
PASS: v0.9.66: recursive playScript exports root + every child + engine/readme
PASS: v0.9.66: duplicate reference to one child source emits one plan file
PASS: v0.9.66: child plans keep recursive INCLUDE links
PASS: v0.9.66: duplicate output-name guard is explicit
PASS: v0.9.66: nested missing-file guard fires in preflight
PASS: v0.9.66: failed include preflight writes zero files
PASS: v0.9.66: include cycle guard reports the chain
PASS: v0.9.66: recursive include depth cap is four
PASS: v0.9.66: forced child-plan publish failure surfaced
PASS: v0.9.66: multi-file rollback restores the complete old bundle
PASS: v0.9.66: rollback removes all transaction artifacts
PASS: v0.9.66: typed stack rejects cross-nested ENDLOOP
PASS: v0.9.66: typed stack rejects duplicate ELSE
PASS: v0.9.66: typed stack rejects package/group cross nesting
PASS: v0.9.66: all generated split runtime modules found for golden compare
PASS: v0.9.66: all embedded split runtime modules are byte-identical to generated goldens
PASS: v0.9.65: the plan exporter targets the current firmware bundle line (PLAN|2)
PASS: v0.9.65: Export writes plan.txt + plan_engine.py + README-PLAN.md
PASS: v0.9.65: the written bundle carries the plan and the real engine
=== Results: 752 passed, 0 failed ===
```
