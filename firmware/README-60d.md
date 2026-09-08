# code60d.py - PRODUCTION firmware: the typeText (KTEXT) fix (2026-09-08)

Built by `tools/make_60d.py` from code60c.py. Validated by `sim/sim60d.py` =
**20 passed / 0 failed** under a simulated CircuitPython-10.3.0 bytearray, a slow-arm
wedge scenario, and a keyboard whose `write` raises (matching the board's real bundle).

## Root cause (proven from the board's own /lib)
The user's `lib.zip` is **adafruit_hid 6.1.10**. Its `keyboard.mpy` strings show only
`press` / `release` / `release_all` / `_add_keycode_to_report` - there is **NO `write`
method**. So the firmware's `KTEXT` handler calling `kbd.write(ch)` raised
AttributeError on the very first char -> `ERR|EXC|KTEXT` -> the run died before typing
anything. This is exactly why Keystroke (`KCOMBO`, which uses press/release) worked but
Type Text never did.

## The fix
`KTEXT` now types via the proven `kbd.press`/`kbd.release` primitives using an inline
US-layout ASCII->keycode map (`_ascii_key`): letters a-z/A-Z (Shift for capitals),
digits 0-9 (reusing the proven DIGITS table), space, and the full common punctuation set
(plain and Shift+). `getattr(..., None)` fallback means a missing name yields
`ERR|ASCII|KTEXT`, never a crash. The per-key humanized delay uses `random.random()`
(not `random.uniform`).

Keeps the 60b PING fix (rebind-by-slice) and the 60c mouse flow control intact.
Version bump `pico-light 0.9.60d`.

## Regenerate
`code60c.py` (see README-60c.md) -> `python3 tools/make_60d.py`.

## TODO (permanent home)
The C# `PicoFirmwareExporter` template still emits `kbd.write(...)` for KTEXT - it must
emit the press/release map (and the slice-rebind fix from 60b, and the flow control from
60c) so future exports are correct. In the Claude Code queue.
