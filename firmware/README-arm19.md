# Arm firmware 1.9 — hand-smooth path interpolation (2026-09-09)

## Why
The user's own hand recording (`my hand.txt`): median **3 px per sample**, **~390 samples/sec**,
median speed **~530 px/s**. The PC->pico->arm chain physically tops out at **~50 fed points/sec**
(~20 ms each, measured), but the arm alone can emit **~100+ HID reports/sec** (its only per-report
cost is the USB HID frame, ~8-10 ms). So the work is split:

- **bridge v3.3** keeps feeding >=25 ms thinned WindMouse points (curve shape + speed profile
  preserved in the point spacing) but streams them as `MMOVE|x,y,abs,2`.
- **fw 1.9** (`mouse_move_stream`) subdivides each fed segment into **<=8 px linear micro-steps**
  (max 3 substeps, so a fast segment never overruns the 25 ms feed cadence) emitted at native
  HID pace -> ~100 reports/sec on the board = hand-smooth, exact landing on the fed target.

## Compatibility
- New bridge + old arm (1.7/1.8): the old parser reads `hm==2` as non-human (strict `hm[0]=='1'`)
  -> a plain per-point jump = the pre-1.9 behaviour. Nothing breaks; smoothness needs the 1.9 flash.
- Old bridge + fw 1.9: paths arrive as abs,0 -> unchanged jumps. No regression either way.
- bridge v3.3 bonus: one safe retry on `ERR|UNKNOWN` (UART glitch; the board answers UNKNOWN only
  to lines it did NOT execute - hardware log 2026-09-09, SETRES <- ERR|UNKNOWN once in ~25 repeats).

## Build & flash (same ISP path as 1.8)
1. Arduino IDE <- `ams_board19.ino` <- Sketch <- Export Compiled Binary -> `ams_board19.ino.arduino_leonardo.hex`
2. `python isp_flash_app.py --port COMx --hex ams_board19.ino.arduino_leonardo.hex` (COMx = programmer board port)
3. Disconnect the programmer RST wire afterwards or the board will not boot.
4. The app status bar should show FW 1.9.

## Validation
- `sim/sim_arm19.py`: **13/0** (subdivision bounds, exact landing, corridor check on a 13-point
  WindMouse-style path, 1.8 graceful degradation, mode 0/1 regression, click-after-path invariant).
- `tools/test_bridge_60e.py` (sandbox suite): **38/0** including the abs,2 emission + UNKNOWN retry.
- Anchored generator: `tools/make_arm19.py`; brace/paren balance identical to the 1.8 base.
- `ams_board19.ino` sha256: `e932dc75ff36b961dbf84c829c8e4baa8ecc0b06b5873049869920c3c61ab29e` (768 lines).

## Later (Claude Code queue)
- Port 60b-60e pico fixes into the PicoFirmwareExporter C# template + apply `tools/patch_bridge_60e.py`
  (v3.3) and `tools/patch-v0.9.61.py` on main -> next CI run/release.
- Optional: app-side path cadence control (HumanMouse) and fw tunables (dist/8, substep cap).
