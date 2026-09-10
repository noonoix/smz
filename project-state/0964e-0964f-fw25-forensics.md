# Link integrity, part 2: 0.9.64e -> 0.9.64f and arm fw 2.4 -> 2.5

Continues `project-state/0964d-fw24-link-integrity.md`. Machine PC-13458, Pico on COM3,
plan `PLAN|1` with `RMOUSE|region=1301,0,378,1049`, recorder = AMS "Record Being Edited".

## 1. What 0.9.64d + fw 2.4 actually fixed

| metric | 0.9.64b | 0.9.64c (framing only) | 0.9.64d + fw 2.4 |
| --- | --- | --- | --- |
| teleports per run | 3 (1139/1287/1276 px) | 3 (1222/1346/1432 px) | 1 (1261 px, then 1398 px) |
| `CKSUM drop` | n/a (no framing) | 41 across three runs | 2 in 43 s, then 0 in 80 s |
| max `_arm_lag` | 6-7 | 6-8 | 1 |
| step median | - | - | 2.24-3.00 px (human: 2.24) |
| speed median | - | - | 186-200 px/s (human: 140) |

Structural cause (proven, unchanged): the arm blocks inside `mouse_move_stream`
(`delay(paceMs)`, `delay(2)`) and does not read `Serial1`; the ATmega32U4 RX buffer is
64 bytes; the brain fed a point every ~10 ms while the arm needs >=20 ms, so ~208 bytes
were in flight against a 64-byte buffer. `ARM_LAG_MAX = 2` caps that at 52 bytes.
Simulation: `PASS: fw2.3 executed 33 unvalidated header-less moves, fw2.4 executed 0`.

## 2. Regression introduced and removed (0.9.64d build 1)

`ARM_BAUD = 57600` was emitted ~60 lines BELOW `busio.UART(..., baudrate=ARM_BAUD, ...)`,
so import raised `NameError`, `except Exception: arm = None` swallowed it and the mouse was
completely dead while the serial log looked clean (only `plan: loaded 7 ops`).
`tools/patch_arm_flow_0964d.py` now emits the constant immediately above the `try:` block
and carries a permanent self-check:

```py
(out.index("ARM_BAUD = 57600") > out.index("baudrate=ARM_BAUD"),
 "ARM_BAUD defined after the UART init: NameError -> arm=None -> dead mouse")
```

## 3. Run 08:58:44 (0.9.64e) - the decisive measurement

Serial: `plan: loaded 7 ops`, 8x `ack watchdog reset (lag was 1)`, **0** CKSUM, **0** NOFRAME,
and 6x `SENT JUMP`:

```
29743  plan: SENT JUMP #1 (1542, 388) -> 1612,825 (dx=70 dy=437)
43812  plan: SENT JUMP #2 (1561, 833) -> 1493,414 (dx=-68 dy=-419)
46921  plan: SENT JUMP #3 (1439, 602) -> 1406,1005 (dx=-33 dy=403)
57566  plan: SENT JUMP #4 (1425, 943) -> 1502,703 (dx=77 dy=-240)
75879  plan: SENT JUMP #5 (1484, 126) -> 1411,324 (dx=-73 dy=198)
77633  plan: SENT JUMP #6 (1438, 388) -> 1555,607 (dx=117 dy=219)
```

All six are INSIDE `region=1301,0,378,1049` (x 1406-1612, y 126-1005) and each sits beside a
coalesce/watchdog event: they are the gap left by dropped mid-path points, which the arm
interpolates across in 3 px micro-steps. Not the bug.

Recorder (2516 samples, 72.2 s, 3 plan repeats, `hello ai` typed correctly 3x, 2 clicks):
exactly ONE jump > 60 px inside the plan window - `t=13770 (305,458) -> (1651,82) d=1398`.
The cursor GLIDED to x=305 in 1-3 px steps first, so the arm interpolated toward a
far-left target: a bad target reached the arm, was accepted, and was executed.

Conclusion: the corrupt target was never in the Pico's sent stream and was never rejected
by the frame checker. Only two mechanisms remain - a corrupt line whose byte-sum still
matches, or a truncated frame spliced onto the next line (checksum computed before the
truncation).

## 4. 0.9.64f (Pico) - `tools/patch_arm_diag_0964f.py`

1. Telemetry moved from `forward_fast` into `_arm_write`, the single place every byte
   leaves the Pico. 0.9.64e sat after the coalesce branch, so the `_pending_move` flush
   inside `pump_arm` (a direct `_arm_write` call) was invisible.
2. Short-write detection: `busio.UART.write()` may write fewer bytes than asked; the
   return value is now checked and `arm: PARTIAL WRITE #n (x of y bytes)` is printed.
3. Drop-aware classification: a jump right after a coalesce drop prints `after-drop`
   (expected); a jump with no drop in between prints `NO-DROP` (a real Pico-side bug).
4. `PING` now reports `...|cksum=%d|noframe=%d|sentjumps=%d|partial=%d`.

Artifact: `code64b.py` 0.9.64f, 41809 bytes,
sha256 `1d1afe089f938968f71e1f67ea4ea6495c072756d3214b7c24e1830a269a565a`,
banner `pico-light 0.9.64f | ... | diag=full`.

## 5. Arm fw 2.5 - `tools/patch_arm_fw25.py`

1. `FW_VER "2.5"`.
2. `g_rawLine1[MAX_PT]` keeps the wire bytes BEFORE `frame_unwrap` rewrites the line in place.
3. `MOVE_SANITY_PX 700`: a streamed point further than that from `g_curX/g_curY` is refused
   (coalesce gaps reach ~437 px, the corrupt targets are 1100-1400 px), `g_badMoves++`, and
   the arm emits `EVT|BADMOVE|n|x,y|from=cx,cy|raw=<exact bytes>` on `Serial1`, which the
   Pico forwards verbatim into the PC capture. `reply_ok("MMOVE")` still fires so the
   brain's ack ledger stays balanced.
4. `OK|VER|...|badmoves=%u`.

Artifact: `ams_board25.ino`, 33121 bytes,
sha256 `4b54d04b328ea7a375daa82786fab733d9ae2055a21f6f72cc1a42164266c16c`.
Flash order matters only when baud changes; 2.4 -> 2.5 keeps 57600, so the arm may be
reflashed independently (ISP, `python isp_flash_app.py --port COM9 --hex ams_board25.ino...hex`).

## 6. Acceptance for the next run

* 0 jumps > 60 px in the recorder plan window
* 0 samples outside `1301,0,378,1049`
* 0 `CKSUM drop`, 0 `NOFRAME drop`, 0 `PARTIAL WRITE`, 0 `SENT JUMP ... NO-DROP`
* `_arm_lag` never above 2
* any `EVT|BADMOVE` line is a PASS for the guard and gives the raw bytes to analyse

Decision table once the next capture arrives:

| observation | verdict |
| --- | --- |
| `EVT|BADMOVE` with a mangled `raw=` | wire corruption that beat the 8-bit sum -> move to length + CRC16 framing |
| `EVT|BADMOVE` with an intact `raw=` | the Pico sent it -> plan engine / coalescing bug |
| `PARTIAL WRITE` lines | truncated frames -> chunk writes and retry on short write |
| `SENT JUMP ... NO-DROP` | Pico-side jump -> plan engine bug |
| none of the above and no teleport | 0.9.64f + fw 2.5 ship; cut 0.9.65 |

## 7. Repo state

* branch `fix/arm-flow-0964d-fw24` (base `8286a2ee`, PR #22 open) now carries
  `tools/patch_arm_flow_0964d.py`, `tools/patch_arm_fw24.py`,
  `tools/patch_arm_diag_0964f.py`, `tools/patch_arm_fw25.py` and both state docs.
* PR #21 (`fix/arm-link-framing-0964c`) is dead: framing alone did not stop the teleports.
  Close it, superseded by #22.
* `ci-22` green on `main` (744 passed / 0 failed).
* Still missing: `firmware/code64b/code64b.py` and the Pro Micro sketch as tracked sources
  (Golden Rule 10). Both are currently reproduced by the patchers above from 0.9.64b /
  `ams_board23.ino`.
