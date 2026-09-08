# code60a-diag.py — diagnostic firmware build (2026-09-08)

One-off diagnostic = the PROVEN `code60a.py` (the v0.9.60a export whose keypad is
confirmed working on the real hardware) + DIAG console logging injected by
`tools/make_diag60a.py`. Built file delivered directly to the user; this note + the
generator + the sim are the recovery path (golden rule 10).

## Why it exists (replacing the separate probe)
- Probe v1 crashed at boot: `os.path` does not exist in CircuitPython.
- Probe v2 booted but its keypad died: it used `Keycode.NUM_LOCK`, which does NOT
  exist in the user's real `lib/adafruit_hid/keycode.mpy` (evidence: only
  `KEYPAD_NUMLOCK`, `SCROLL_LOCK`, `CAPS_LOCK` are present). The wrong name raised,
  the guard set `hid=no`, and `pump_keys` bailed out. Both were probe-side bugs,
  not the hardware — `code60a.py` uses the correct `Keycode.KEYPAD_NUMLOCK` and its
  keypad works.
- So DIAG logging now rides on the proven firmware: keypad stays alive AND we watch
  the data port.

## What it logs (CONSOLE port; read with `python tools\pico_console.py COM3`)
- `DIAG60a boot ok | hid=.. | dataport=.. | sensor=.. | arm=..` at boot
- `DIAG rx chunk n=.. hex=..` for every chunk arriving on the DATA port
- `DIAG rx line: ..` for every assembled command line
- `DIAG tx: ..` / `DIAG tx ERR|EXC|..` for every reply written
- `DIAG alive | hid=..` heartbeat every 2 s in the idle branch

`_diag_print` prints only when the console is connected, so the loop never blocks
when pico_console is detached.

## Regenerate (sandbox-reset-proof)
1. `code60a.py` = `firmware/pico-light-0.9.60-template.py` filled with:
   machine=PC-13458, generated=2026-09-08 12:15, version=0.9.60, states=1,
   loop=forever/0/0 (same values `sim/sim60.py` uses).
2. `python3 tools/make_diag60a.py`  (reads /data/code60a.py, asserts exactly the two
   intended lines change, writes /data/code60a-diag.py, compile-checks it).

## Validation
`sim/sim60diag.py` (fake-hardware harness): **26 passed / 0 failed** — boot banner,
PING→PONG with full DIAG trail (chunk hex + line + reply), malformed line → ERR|EXC
and loop survives, HALT acked and forwarded to the arm, keypad GP4=KEYPAD_NUMLOCK /
GP3=SCROLL_LOCK intact, boot without sensor, heartbeat, hygiene (no `os`, no
`Keycode.NUM_LOCK`, plain decode, all DIAG markers present).

## Test protocol (decides the PING-silence direction)
1. Copy `code60a-diag.py` as `code.py` onto CIRCUITPY (keep the existing `boot.py`).
2. Unplug/replug the Pico — keypad must work again (proven base).
3. Device Manager: the Pico must add TWO new COM ports (console + data). If only ONE
   appears, the data port never enumerates on Windows = that is the whole bug.
4. Run `python tools\pico_console.py COM3`; DURING its 20 s window do
   Disconnect/Connect with AUTO in the app; send the console output:
   - `DIAG rx line: PING` + `DIAG tx: OK|PONG` seen -> bytes arrive and the reply is
     written (bug is on the host/bridge read side).
   - no `DIAG rx chunk` at all -> bytes never reach the Pico (Windows port/driver).
5. After diagnosis, flash the clean 60a `code.py` back.

## Host-side note (bridge.py read this session)
`detect_board_port()` probes every candidate port with `PING\n` at a 0.8 s timeout and
returns the first port whose reply contains role=brain/pico-light, else any
PONG/HELLO/OK, else the highest-scored candidate (the two Pico ports score 100 via
VID 0x2E8A). If the data port stays silent the probe can land on the console port or
the arm — the DIAG log disambiguates which leg is actually broken.
