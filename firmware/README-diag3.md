# code60a-diag3.py - diagnostic + candidate fix (2026-09-08)

Diag3 = the PROVEN `code60a.py` + DIAG logging + a CP-safe parse fallback. Built by
`tools/make_diag3.py`, validated by `sim/sim60diag3.py` (28 passed / 0 failed).

## Why
Hardware (diag1) proved: the PING chunk ARRIVES at the data port (hex 50494e470a =
"PING\n") but the line is NEVER assembled (no DIAG rx line, no PONG). pump_arm proves
bytearray.find works, so the failing op is in the PARSE step: bytes(bytearray) /
del-slice / bytes.decode - all introduced by the 0.9.59h byte-buffer rewrite and
silently swallowed by the never-die guard. The pre-0.9.59h string-buffer build
answered PING on hardware.

## What diag3 does differently
- Manual newline scan (len + int-index only; no bytearray.find) -> "DIAG scan nl=.."
- Primary parse (bytes/decode/slice-rebind) wrapped -> "DIAG primary-parse OK" or
  "DIAG primary-parse EXC <the real failing op>"
- CP-safe fallback (chr() build + slice-rebind; no bytes/decode/find/del) ->
  "DIAG fallback-parse OK", so PING still gets answered even if the primary op is bad
- The never-die guard now SPEAKS: "DIAG loop EXC <real error>"
- sys.version logged at boot
- keypad path untouched (Keycode.KEYPAD_NUMLOCK preserved)

## Read the result
Flash as code.py, replug, run `python tools\pico_console.py COM3`, then in the app do
Disconnect/Connect with AUTO during the 20 s window:
- "DIAG rx line: [PING]" + "DIAG tx: OK|PONG" -> line assembles and answers. If the
  app now connects as brain, the bug was the parse step (the fallback fixed it).
- "DIAG primary-parse EXC <op>" names the exact CircuitPython-incompatible operation
  to fix permanently in the exporter.
- still no "DIAG scan" after a chunk -> the failure is earlier (extend/read) - the
  speaking guard (DIAG loop EXC) will name it.
After diagnosis, flash the clean 60a code.py back.
