# code60b.py - PRODUCTION firmware, the permanent PING fix (2026-09-08)

Built by `tools/make_60b.py` from the proven `code60a.py`. Validated by
`sim/sim60b.py` = **18 passed / 0 failed**, run under a simulated CircuitPython-10.3.0
bytearray that REJECTS slice deletion (the exact hardware error diag3 caught).

## Root cause (hardware-confirmed by diag3)
diag3 log on the real board:
```
DIAG primary-parse EXC TypeError("'bytearray' object doesn't support item deletion")
DIAG fallback-parse OK
DIAG rx line: [PING]
DIAG tx: OK|PONG|...            <- app then connected as role=brain, pico=on, arm=on
```
CircuitPython 10.3.0 bytearray does NOT support slice deletion, so
`del buffer[:nl+1]` threw TypeError on EVERY complete line, and the silent never-die
guard swallowed it -> PING never answered, app fell back to the arm. This was
introduced by the 0.9.59h byte-buffer rewrite (the old string-buffer build answered
PING fine).

## The fix (minimal, both RX paths)
`bytes()`/`decode()` were fine; only the slice-delete threw. Replaced rebind-by-slice:
- `del buffer[:nl+1]`   -> `buffer = buffer[nl+1:]`      (main PC data port)
- `del buffer[:-1024]`  -> `buffer = buffer[-1024:]`     (main runaway guard)
- `del _arm_buf[:nl+1]` -> `_arm_buf = _arm_buf[nl+1:]`  (arm pump line consume)
- `del _arm_buf[:-256]` -> `_arm_buf = _arm_buf[-256:]`  (arm runaway guard)
- pump_arm gains `global _arm_buf` (rebinding inside a function needs it)
- PING identity bumped to `pico-light 0.9.60b` so the app proves the fix is live

No DIAG logging (this is clean production firmware). Keypad, light sensor, mouse/sound
forwarding, never-die guard - all unchanged.

## Regenerate
`code60a.py` = `firmware/pico-light-0.9.60-template.py` filled with machine=PC-13458 /
generated 2026-09-08 12:15 / version 0.9.60 / 1 state / forever/0/0. Then
`python3 tools/make_60b.py`.

## TODO (permanent home)
The same slice-delete pattern lives in the C# `PicoFirmwareExporter` template -
Claude Code must apply the same rebind-by-slice fix there so future exports don't
reintroduce the bug.
