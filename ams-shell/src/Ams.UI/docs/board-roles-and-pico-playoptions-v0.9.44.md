# v0.9.44 — rail leave-close · parallel-group vein · Pico play options · board LEDs · keyboard board

Five user-reported items (2026-09-04, on the v0.9.43 build):

1. **Rail submenu stayed open after the mouse left the rail** — the rail Border now has
   `MouseLeave="RailBorder_MouseLeave"`: after a 400 ms grace delay (so the pointer can travel
   into the open menu) the menu closes unless it is itself hovered (`menu.IsMouseOver`). The
   reference check (`ReferenceEquals(_openRailMenu, menu)`) keeps rapid sibling hovers safe.
   The ▾ caret click path also records `_openRailMenu`, so click-opened menus close too.
2. **Parallel Group showed no red vein** — root cause: `Renumber`'s scope registration
   (`opensLoop || opensIf || opensPackage`) never included `parallelGroup`, so no
   `_scopeRanges` entry existed for it. Added `opensParallel`; also taught `IsScopeMarker`
   that a parallel group has no closing marker (without that guard, a parallel group sitting
   at the end of an If block would swallow the parent's `# End If` row into its scope).
3. **Pico export must respect Play Options** — `PicoFirmwareExporter.Export/BuildCodePy`
   gained optional `loopMode/loopCount/loopSeconds` parameters (defaults = the old forever
   behavior); the VM bakes the live Play Options (once / N times / timed with the
   second-minute-hour unit) into `code.py` as `LOOP_MODE/LOOP_COUNT/LOOP_SECONDS`, and the
   standalone armed-states loop now runs through a `loop_due()` gate. README-FLASH.md states
   the baked options. Note: this governs the Pico's STANDALONE (hostless) runs; while the PC
   drives, the app's own Play Options already applied.
4. **Per-board presence LEDs** — after connect, the app sends `PING` and parses the reply
   (`MainViewModel.ParseBoardPresence`, public static for tests): a `role=brain`/`pico-light`
   answer lights the Pico LED, `arm=promicro` (or a plain firmware-1.6 board) lights the
   Pro Micro arm LED. Both go out on disconnect. Two labeled ellipses in the status bar
   (green #3FB950 when on, gray #3A4048 when off).
5. **Flexible keyboard executor** — Options → General now asks «کیبورد را اجرا کند: پیکو
   (مغز) / پرو میکرو (بازو)» (`AppSettings.KeyboardBoard`). The exported `code.py` honors it:
   `KBD_ON_ARM = True` forwards KTEXT/KCOMBO/KDOWN/KUP to the arm over UART (with a
   length-proportional timeout for KTEXT); `False` runs them locally — the template now
   actually implements keyboard handling (`handle_keyboard`, modifiers via the new `MOD_VK`
   map, ASCII-only KTEXT with per-key random delay, mirroring the firmware-1.6 protocol).
   `BundleVersion` bumped to 0.9.44.

Tests: Step 44 adds 16 assertions (`Assert(` total 427). Expected: **464 passed / 0 failed**
(448 executed in the v0.9.43 run + 16). The generated `code.py` was compile-checked in three
configurations (timed/once/forever × arm on/off) with zero unreplaced placeholders.
