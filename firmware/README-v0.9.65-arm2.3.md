# v0.9.65 (Pico) + arm fw 2.3 — 14k-record mouse fixes

Field evidence: 2026-09-09 board-output record (25,488 lines / 13,984 mouse samples / 202.4 s / 5 Start-Stop cycles) on code64 + arm 2.2.

## Root causes
1. **Rare dart (~every 25 s):** a lost `OK|MMOVE` on the unframed pico↔arm UART pushed ack lag past `ARM_LAG_MAX=8`; Pico coalesced to the newest target and arm fw 2.2 played the ~450 px catch-up as 8 instant ~57 px steps in <=20 ms (~18,000 px/s).
2. **One 1500 px out-and-back (t=150.1 s):** a byte-dropped `MMOVE` (`1532` -> `32`) executed as written, outside the plan region.

## Fixes built
- **code65.py / pico-light 0.9.65:** `_flush_pending()` splits catch-up jumps over 140 px into `ceil(dist/140)` paced hops (cap 8, 20 ms gap), using `_arm_last_target` as a shadow of commands actually written to the arm. Each hop is included in the ack-lag ledger.
- **Negotiated framing:** `#` + 2 hex byte-sum + `|` + payload. Pico probes legacy `VER`; arm fw 2.3 advertises `|FRM` only on Serial1. Bad frames return `ERR|CKSUM` and are never executed. Legacy wire remains byte-identical when framing is off.
- **ams_board23.ino / fw 2.3:** streamed points <=60 px retain the <=20 ms behaviour; larger catch-ups sweep at about 2500 px/s, with at most 60 microsteps and 160 ms total. `frame_unwrap()` is inside `serial1_line_ready()`, covering main-loop and sound-wait abort paths.

## Compatibility
- code65 + arm 2.2: works in legacy mode; hop fix active.
- code65 + arm 2.3: hop fix + framing + paced catch-up active.
- code64 + arm 2.3: legacy commands remain accepted.

## Validation
- `sim_code65fx.py`: **32/0** — negotiation, checksum math, hop splitting including watchdog path, lag accounting, checksum-drop ledger, EVT passthrough.
- `sim_arm23.py`: **28/0** — pacing budgets, <=8 px microsteps for catch-ups <=480 px, checksum rejection, legacy passthrough.
- `py_compile` on code65; both anchored generators idempotent; arm brace/paren deltas unchanged from fw 2.2.

## Delivered artifact
`Classroom-Studio-mousefix-v0.9.65-arm2.3.zip`
- code65 SHA-256: `9c98b171303232e75eb8224b805332dcccf953990cbd80b0d4dab57c4dfd3b9e`
- arm23 SHA-256: `882d7132d461118fd4f48102be219eeeac38c042443375cb44d5b890d2f821ad`
- bundle SHA-256: `3991dd06bc8ad8aa7fb46257c43657a72d06fa8711387041ce3f52321ca68a0b`
