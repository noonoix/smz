# code60c.py - PRODUCTION firmware: the dense-mouse-path wedge fix (2026-09-08)

Built by `tools/make_60c.py` from code60b.py. Validated by `sim/sim60c.py` =
**23 passed / 0 failed**, under a simulated CircuitPython-10.3.0 bytearray (no slice
delete) AND a slow arm that reproduces the dense-path backlog the user hit.

## The bug (hardware log)
Connected fine (role=brain), keyboard typed, mouse moved - but:
- per-move `OK|MMOVE` acks piled up (241 per path, PC reads 1 per 12) -> mis-paired
  replies (`SETRES` answered by a stale `OK|MMOVE`)
- 4th dense move -> `Write timeout` (PC side) -> the USB link wedged
- the next run could not even SETRES (port stuck until replug)
- motion felt choppy

Root cause: the firmware acks EVERY MMOVE micro-step to the PC. But mouse moves are
sent via `send_path` which is WRITE-ONLY (never reads per-move acks) + a periodic PING
drain. So the acks are pure backlog that fill the Pico's USB TX buffer ->
_serial_write_line blocks -> the loop stops reading USB RX -> PC write times out.

## The fix
1. **MMOVE fire-and-forget**: no per-move ack to the PC (send_path never reads them).
   Discrete mouse (MCLICK/MWHEEL/MDOWN/MUP) still fire-and-ack. -> kills the USB TX
   backlog AND the reply mis-pairing.
2. **Arm flow control with absolute-move coalescing**: track `_arm_lag` (MMOVEs written
   minus the arm's OK|MMOVE acks). Once the arm is ARM_LAG_MAX behind, coalesce to the
   NEWEST absolute target instead of blocking; flush the latest target when the arm
   catches up. Absolute moves make dropping intermediate points safe; the cursor still
   lands on target. -> prevents the arm UART from wedging the link.
3. Main loop skips a `None` reply (the fire-and-forget MMOVE).
4. Version bump `pico-light 0.9.60c`.

Keeps the 60b PING fix (rebind-by-slice) intact. Keypad/sensor/sound unchanged.

## Regenerate
`code60b.py` (see README-60b.md) -> `python3 tools/make_60c.py`.

## Note on smoothness ceiling
The double hop PC -> Pico -> arm runs over a 115200-baud UART. That is the smoothness
cap. For visibly smoother long paths later, raise the arm UART baud (needs an arm
reflash) - not a Pico-side change.
