# Phase 7 handoff — 2026-09-17

## Synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records technical checkpoints, evidence, hashes, safety gates, fixes, and exact next actions. The full chat transcript is intentionally not copied. This file stays on `docs/session-2026-09-17-handoff` so documentation commits do not alter code-artifact provenance.

## Current state

- Repository: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Draft PR: https://github.com/c4haztex/smc-1/pull/175
- Current validated code head: `172528e1fb2c1430ef03f7395c74f7e92a43a1f5`
- Current Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35259238518
- CI: 12 executable checks succeeded; downloadable package skipped by branch condition.
- Installed hardware bundle: `stage12` (does not yet include the latest workflow refinements).
- Board: COM30/COM31 hot-plug detected; COM31 automatically selected; `role=brain` confirmed.
- Hardware passed: Boot, control plane, compact light telemetry, `SETRES`, live Buzzer Step, calibration-entry cue, and stable Desktop sample-complete cue.
- Next package to build and validate: `stage13` from the current artifact.

## Fixed wiring and controls

- BH1750/GY-30: 3V3, GND, SDA=GP20, SCL=GP21, address `0x23`.
- GP4 blue square button: long hold enters/exits calibration; short press advances position; after position 6 it wraps to position 1 when no sample or unsaved result is pending.
- GP3 yellow round button: held during boot for maintenance; inside calibration it starts a sample, saves a completed sample, and—after a successful save—starts a fresh sample for the same position when pressed again.
- GP6: passive piezo.
- UART0 to arm: GP16 TX, GP17 RX, 57600 8N1, common ground.
- Keep Light Watch off during physical calibration; keep Classroom Studio connected and green.

## Calibration profiles and audio contract

1. `desktop` — 262 Hz
2. `login-or-dc` — 294 Hz
3. `character-dashboard` — 330 Hz
4. `entering-game-loading` — 349 Hz
5. `game` — 392 Hz
6. `targeted` — 440 Hz

Audio meanings:

- One position-specific note: entered/advanced/wrapped to that profile.
- Two pulses of the current profile note: five-second sample completed successfully and is ready to save.
- Ascending `880 → 1320 Hz`: save/re-save succeeded.
- Six-note melody after the first successful save of all six profiles: full calibration set completed.
- No success tone is emitted after a failed save.

Sampling uses a five-second window, median center, minimum five readings, maximum spread 5 lux, tolerance `max(2.0, spread * 1.5)`, and `stable_ms=750`.

## Current button state machine

For one profile:

1. Yellow short press while ready → begin five-second sample.
2. Successful sample → double current-profile tone; result is pending and not yet saved.
3. Yellow short press → persist the result; success melody confirms storage.
4. Yellow short press again while still on the same saved profile → start a fresh five-second sample in place (`retry=1`).
5. The previously persisted value remains valid during this retry. It is replaced only after the retry completes successfully and yellow is pressed again to save.
6. Blue short press → advance to the next profile; from profile 6, wrap to profile 1 when safe.

Safety rules:

- Do not advance or wrap while sampling.
- Do not advance or wrap while a completed result is awaiting save.
- A failed/unstable retry does not erase the previously persisted calibration.

## Relevant fixes

| Commit | Change |
|---|---|
| `67ab1edf2cae12985d344ec37f5ad97a1b2071d0` | Filesystem persistence and GP3 maintenance contract. |
| `dd006a370bf6b43c17ed5f17709ca7815fd76ab5` | Calibration audio cues and six distinct profile notes. |
| `9d32e09bd6e53fc506f847bff3fc28ad1fa64a8c` | Compact light-response parser. |
| `a84849447fe6773dd1a006ec0e8582c1161c56c5` | Pico-local live `SETRES`/`BEEP` and GP6 output. |
| `88ff59fcbb8d6c0613e2f76ee77c9f9da766f893` | Buzzer-to-`BEEP/DELAY` Combined Guard route adapter. |
| `79b4618700bd5a275d6241363d1e00ba43573184` | Removed the second legacy strict-plan export rejection path. |
| `1be2b9342bcdbb7be69bba6328dcbe665c6f8027` | Added save-success cue and safe profile-6-to-profile-1 wrap. |
| `172528e1fb2c1430ef03f7395c74f7e92a43a1f5` | Added same-profile resampling after save and preserved the prior saved value until explicit replacement. |

Earlier Boot fixes remain in force: low-memory import ordering/deferred plan engine, CircuitPython `os.path` compatibility, 20-payload manifest alignment, and `hashlib.new("sha256")` compatibility.

## Bundle and hardware evidence

### `stage11`

- ZIP SHA-256: `1293441adaf1122e6587b4ee8bc3c3c1f1376615a0097dc84ca630f52d2e039e`
- Auto-port, persistence, calibration audio, and compact light parser baseline.

### `stage12`

- ZIP SHA-256: `6ad814f2311d9ee25c3d9554cf3d85410e8d696b11fee9b8a35c279265613c25`
- Exactly 21 files and 20 manifest entries.
- Zero hash mismatches, unsafe paths, or Python syntax errors.
- Boot/GP3, `role=brain`, `SETRES`, `BEEP`, GP6, and six calibration notes present.
- Installed successfully on the Pico.

Hardware evidence:

```text
hot-plug: board detected on COM30, COM31 — connecting automatically
port_open: COM31
connected: ...|profiles=6|role=brain
→ SETRES|1920,1080
← OK|SETRES
→ BEEP|2637,66
← OK|BEEP
...
run finished
```

Every live BEEP received `OK|BEEP`; the user confirmed audible output. With Light Watch disabled, a long GP4 hold produced the calibration-entry cue. A short yellow press followed by a stable wait produced the expected successful sample-complete alarm for Desktop. Classroom Studio currently does not surface unsolicited physical-button `EVT|CAL|...` lines in its UI log; audio is therefore the immediate physical feedback.

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute operational routes, macros, HID actions, or actuators.
- Do not create or copy `ams_key.json`.
- Keep PR #175 Draft; do not merge or release.
- Route serialization and first non-empty-route memory behavior remain separate unapproved gates.
- Do not continue real calibration on `stage12`; it lacks the new save-success, wrap, and same-position retry behavior.

## Exact next action

1. Download `light-state-windows-output` from run `35259238518`.
2. Extract it into a new Windows folder and launch that build.
3. Export Combined Portable Guard into a clean staging folder.
4. Send the archive as `stage13.zip` for validation before copying anything to `CIRCUITPY`.
5. After validation, install the 20 payload files and replace `SHA256SUMS.txt` last while booted in GP3 maintenance mode.
6. Re-run the controlled audio/state-machine checks before continuing profile calibration.
