# Link integrity: v0.9.64d (Pico) + arm fw 2.4

## What 0.9.64c missed

0.9.64c added `#XX|` integrity frames on the Pico -> arm UART. The hardware
re-test (2026-09-10) proved the frames work (41 `CKSUM drop` lines across three
runs, none executed) but the teleport survived. Recorder trace of the 58 s run:

| t | from | to | distance |
|---|---|---|---|
| 34.2 s | (349, 519) | (1537, 232) | 1222 px |
| 44.0 s | (263, 406) | (1580, 685) | 1346 px |
| 54.8 s | (221, 488) | (1597, 92) | 1432 px |

Every source x is exactly 1000 px below a valid in-region coordinate
(1349 / 1263 / 1221), i.e. the leading `1` was still lost *and executed*.

## Measured mechanism

Serial logs show bursts of CKSUM drops that always start right after
`ack watchdog reset (lag was 1)` and end at `lag was 6..7`. That is the arm's
64-byte `Serial1` RX buffer overflowing:

* `mouse_move_stream()` blocks 20..160 ms per point (`delay(paceMs)`) and does
  not read `Serial1` during that time.
* `plan_engine` feeds a point every ~10 ms, so the queue grows ~2x faster than
  the arm drains it.
* `ARM_LAG_MAX = 8` allowed ~208 bytes in flight against a 64-byte buffer.

The overflow drops a multi-byte **chunk**, which can swallow the `#XX|` header of
the next line. fw 2.3 then hits its legacy escape hatch:

```c
if (line[0] != '#') return true;   // legacy: pass through
```

and executes the header-less remnant (e.g. `MMOVE|349,520`) with no validation.

## The two fixes

### Pico v0.9.64d (`tools/patch_arm_flow_0964d.py`)

* `ARM_LAG_MAX` 8 -> 2: never more than ~52 bytes in flight, under the 64-byte buffer.
* Dense path points are dropped instead of queued (`_moves_dropped` counter).
  The arm interpolates 3 px micro-steps, so the visible motion is unchanged.
* Internal UART 115200 -> 57600 (`ARM_BAUD`) for edge margin on the BSS138 shifter.
* `PING` now reports `framing`, `baud`, `lagmax`, `dropped`.

### Arm fw 2.4 (`tools/patch_arm_fw24.py`)

* `g_framedLink` latches once a valid frame is verified; after that a line
  without a `#` header is refused and answered with `ERR|NOFRAME`.
* `Serial1.begin(BRAIN_BAUD)` = 57600, matching the Pico.
* Legacy Picos still work until the first framed line arrives.

## Simulation (`sim/sim_arm_overflow.py`)

Same damaged byte stream fed to both firmwares:

```
fw2.3: UNVALIDATED moves executed = 10 / 13 / 10  (seeds 7 / 11 / 23)
fw2.4: UNVALIDATED moves executed = 0  / 0  / 0
ARM_LAG_MAX=8 -> 208 bytes in flight vs RX_BUF=64  OVERFLOWS
ARM_LAG_MAX=2 ->  52 bytes in flight vs RX_BUF=64  safe
PASS: fw2.3 executed 33 unvalidated header-less moves, fw2.4 executed 0
```

## Acceptance on hardware

1. Zero `CKSUM drop` / `NOFRAME` lines in a 60 s plan run.
2. `arm: ack watchdog reset` lag never above 2.
3. Recorder trace: zero jumps > 60 px and zero samples outside the region.

## Flashing order

Flash the arm (fw 2.4) **first**, then the Pico (0.9.64d). Mixing 0.9.64d with
fw 2.3 works but stays exposed to the legacy hole; mixing 0.9.64c with fw 2.4
breaks the link because of the baud mismatch.
