# Phase 7 handoff — 2026-09-17

## Synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records technical checkpoints, evidence, hashes, safety gates, fixes, and exact next actions. The full chat transcript is intentionally not copied. This file stays on `docs/session-2026-09-17-handoff` so documentation commits do not alter code-artifact provenance.

## Current state

- Active repository: `bermoods/smm`
- Original repository mirror source: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Old Draft PR: https://github.com/c4haztex/smc-1/pull/175 (PR metadata itself was not migrated; branch content was mirrored.)
- Last validated pre-migration code head: `388bc0551bb9196dcf2a2933b45d7f3d33ccbac3`
- Latest active branch head: `4c14f7e422ff2c74f338d1aa7649cee0e5af7762`
- Latest functional code change: `4c14f7e422ff2c74f338d1aa7649cee0e5af7762`
- Current Windows artifact run before migration: https://github.com/c4haztex/smc-1/actions/runs/35261951361
- CI: pre-migration head had 12 executable checks succeeded; post-migration cleanup has not yet produced a validated artifact.
- Installed hardware bundle remains `stage12`; it does not contain the latest calibration/control-audio changes.
- Board: COM30/COM31 hot-plug detected; COM31 automatically selected; `role=brain` confirmed.
- Hardware passed: Boot, control plane, compact light telemetry, `SETRES`, live Buzzer Step, calibration-entry cue, and stable Desktop sample-complete cue.
- Next package: export and validate a fresh package from run `35261951361`; use a new name such as `stage14.zip` to avoid confusing it with any package made from the previous run.

## Repository rescue and active remote

The old repository was mirrored to `bermoods/smm` after Actions on the old account became unavailable. The local rescue verified a complete Git bundle with 233 refs and pushed all normal branches and tags to the new private repository. GitHub-internal `refs/pull/*` refs were rejected by design and are not required because their source branches were preserved.

- New active repository: https://github.com/bermoods/smm
- New `main` after removing the temporary rescue workflow: `e064bfbcd8e7cf8ddb928d28bf41ea7826ae8316`
- New `phase7/light-guard-calibration` after removing the temporary rescue workflow: `3c97560ea0f0200543d4e9abd68d5100fb7e5f79`
- Functional code commit added before rescue cleanup: `2c2a9c8700ba617d6431b2b8410e4bb17765811c`
- Local offline rescue bundle verified by the user: `C:\Users\wasteland\repo-backups\smc-1-complete-rescue.bundle`

## Post-migration functional changes

The active Phase 7 branch now includes board-owned two-second feedback tones for the non-calibration controls:

- Guard Start: distinct two-second tone.
- Guard Stop/HALT: distinct two-second tone.
- Pause: distinct two-second tone.
- Resume: distinct two-second tone.

These tones are played by the Pico on GP6 and do not depend on the route engine or Arduino arm. The static audio contract test now also asserts these bindings. The Classroom Studio calibration protocol contract now includes a parity case proving the same median/spread/tolerance/stable-ms math used by physical button calibration: median center, reject spread over 5 lux, `tolerance=max(2.0, spread*1.5)`, and `stable_ms=750`.

## Fixed wiring and controls

- BH1750/GY-30: 3V3, GND, SDA=GP20, SCL=GP21, address `0x23`.
- GP4 blue square button: long hold enters/exits calibration; short press advances position; after position 6 it wraps to position 1 only when no sample or unsaved result is pending.
- GP3 yellow round button: held during boot for maintenance; inside calibration it starts sampling, saves a completed sample, and after a successful save can start a fresh sample for the same position.
- GP6: passive piezo.
- UART0 to arm: GP16 TX, GP17 RX, 57600 8N1, common ground.
- Light Watch must remain off during physical calibration; Classroom Studio may remain connected and green.

## Calibration profiles

1. `desktop` — 262 Hz
2. `login-or-dc` — 294 Hz
3. `character-dashboard` — 330 Hz
4. `entering-game-loading` — 349 Hz
5. `game` — 392 Hz
6. `targeted` — 440 Hz

Sampling uses a five-second window, median center, minimum five readings, maximum spread 5 lux, tolerance `max(2.0, spread * 1.5)`, and `stable_ms=750`.

## Final audio contract

- Position entry/advance/wrap: one 220 ms position-specific note.
- Yellow accepted for recording or re-recording: one short `660 Hz / 65 ms` cue immediately when sampling begins.
- Stable sample completed: two pulses of the current position note (`110 ms`, pause, `190 ms`).
- Save or re-save succeeded: ascending `880 Hz → 1320 Hz` success cue.
- First successful completion of all six profiles: six-note completion melody.
- Failed saves do not produce a success cue.

## Explicit yellow-button state machine

The yellow workflow is now implemented as explicit branches rather than relying on the legacy `result is not None` delegation:

1. If not calibrating, retain Pause/Resume behavior.
2. If already sampling, emit Busy and do not start a second sample.
3. If a completed unsaved dictionary result exists, save it.
4. Otherwise, begin a fresh sample explicitly:
   - `retry=0` for the first sample at that position;
   - `retry=1` when the same position had already been saved.
5. Emit the `mode=started` event and immediately play the short 660 Hz record-start cue.
6. During same-position retry, the previous persisted calibration remains valid. It is replaced only after the new sample completes and yellow is pressed again to save.

Expected sequence for a saved profile:

```text
short yellow → 660 Hz start cue
wait 5 seconds → double position-note completion cue
short yellow → 880→1320 Hz save-success cue
short yellow again → 660 Hz retry-start cue for the same position
```

## Relevant commits

| Commit | Change |
|---|---|
| `67ab1edf2cae12985d344ec37f5ad97a1b2071d0` | Filesystem persistence and GP3 maintenance contract. |
| `dd006a370bf6b43c17ed5f17709ca7815fd76ab5` | Calibration audio cues and six position notes. |
| `9d32e09bd6e53fc506f847bff3fc28ad1fa64a8c` | Compact light-response parser. |
| `a84849447fe6773dd1a006ec0e8582c1161c56c5` | Pico-local live `SETRES`/`BEEP` and GP6 output. |
| `88ff59fcbb8d6c0613e2f76ee77c9f9da766f893` | Buzzer-to-`BEEP/DELAY` Combined Guard route adapter. |
| `79b4618700bd5a275d6241363d1e00ba43573184` | Removed the second legacy export rejection path. |
| `1be2b9342bcdbb7be69bba6328dcbe665c6f8027` | Added save-success cue and safe profile-6-to-profile-1 wrap. |
| `172528e1fb2c1430ef03f7395c74f7e92a43a1f5` | First same-position retry implementation. |
| `388bc0551bb9196dcf2a2933b45d7f3d33ccbac3` | Reworked yellow into explicit sample/save/retry branches and added the 660 Hz record-start cue. |

Earlier Boot fixes remain in force: low-memory import ordering/deferred plan engine, CircuitPython `os.path` compatibility, 20-payload manifest alignment, and `hashlib.new("sha256")` compatibility.

## Bundle and hardware evidence

### `stage12`

- ZIP SHA-256: `6ad814f2311d9ee25c3d9554cf3d85410e8d696b11fee9b8a35c279265613c25`
- Exactly 21 files and 20 manifest entries.
- Zero hash mismatches, unsafe paths, or Python syntax errors.
- Installed successfully; live Buzzer Step passed.

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

The user confirmed audible Buzzer output, calibration-entry audio, and the stable sample-complete alarm. Classroom Studio currently does not surface unsolicited physical-button `EVT|CAL|...` lines in its UI log, so audio is the immediate physical feedback.

## Diagnosis of “behavior did not change”

The board still runs a bundle without the latest workflow code unless a package exported from the corresponding new artifact is installed. Merely launching a newer Windows build does not update Pico firmware. The retry logic has now also been rewritten explicitly and covered by static contract tests, but hardware confirmation requires a newly exported and validated bundle.

## `stage13.zip` validation

The user provided `stage13.zip` from the migrated repository artifact flow. Validation passed.

- ZIP SHA-256: `c5e7332341d122e0b9f45fdabbc990df61924a08cf62a634b4c35336735c71ba`
- Exactly 21 files.
- No unsafe paths.
- `SHA256SUMS.txt`: 20 entries, 0 missing files, 0 hash mismatches.
- JSON files parse successfully: `guard-calibration.json`, `guard-transition.json`, `pico-calibration.json`.
- Generator: `Classroom Studio v0.9.67`.
- `hardwareCalibrationVerified: false`.
- Python syntax: 8 files, 0 syntax errors.
- `code.py` SHA-256: `1efde414f4b593c53345f6acac60ea5fa7a9b1ec6a24c99a24f11280cf7a6625`.
- `combined_guard_runtime.py` SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`.
- Runtime normalized size remains 20,200 bytes.
- No real `adafruit_hid` import and no `class Keycode`.
- Internal `Keyboard` and `release_all()` remain present.
- New audio contracts are present: record-start `660 Hz / 65 ms`, save-success `880 → 1320 Hz`, and distinct two-second Start/Stop/Pause/Resume tones.
- Same-position retry marker and final-position wrap are present.
- Pico-local host `BEEP` and `role=brain` remain present.

Important: the package's `guard-calibration.json` contains the exported/default calibration values with revision `guard-bf2929070db779e4`, not the five profiles physically saved on the board. A full copy of this package to `CIRCUITPY` would overwrite the board's current physical calibration. Before installing `stage13`, copy the current board `guard-calibration.json`, `guard-transition.json`, and `SHA256SUMS.txt` out of `CIRCUITPY` and validate/merge them, or intentionally accept resetting calibration.

## Rhythmic board-control audio update

The previous two-second continuous Start/Stop/Pause/Resume tones were replaced with short rhythmic signatures. This avoids a stuck-alarm feel and makes the four board-owned controls easier to distinguish.

- Commit: `4c14f7e422ff2c74f338d1aa7649cee0e5af7762`
- Start: rising 5-event pattern, about 880 ms total.
- Stop/HALT: descending 5-event pattern, about 920 ms total.
- Pause: repeated 3-note pattern with rests, about 900 ms total.
- Resume: rising/moving 5-note pattern, about 900 ms total.
- Static contract updated to require 3-6 audible notes per pattern, total duration 850-1100 ms, valid frequency range, four distinct patterns, and the existing Start/Stop/Pause/Resume bindings.
- Local static test passed before commit.
- PR #3 CI after commit: 12 executable checks succeeded; downloadable package skipped by branch condition. Main Windows artifact run: https://github.com/bermoods/smm/actions/runs/35283172213

The user log after replacing the previous package shows the board booting and connecting successfully on COM31 with `combined-pico-guard-executor|hid=on|uart=on|profiles=6|role=brain`. This confirms Boot/control-plane connectivity for the installed package, but the rhythmic update requires a new artifact/package from commit `4c14f7e...` before hardware audio confirmation.

## `stage14.zip` rhythmic package validation

The user provided `stage14.zip`, exported from the rhythmic Windows artifact. Validation passed.

- ZIP SHA-256: `7a8a275f026d53d9fec6a3460ba9f722eb418fe0f9c4fc94f7f72b7542f144f3`
- Size: 38,124 bytes.
- Exactly 21 files and no unsafe paths.
- Required files present: `boot.py`, `code.py`, `combined_guard_runtime.py`, Guard protocol/transition/runtime files, `guard-calibration.json`, `guard-transition.json`, `pico-calibration.json`, `README-FLASH.md`, and `SHA256SUMS.txt`.
- `SHA256SUMS.txt`: 20 entries, no duplicates, no missing files, no hash mismatches.
- JSON files parse successfully and `guard-calibration.json` matches `guard-transition.json` for all six profiles.
- Calibration revision remains `guard-bf2929070db779e4`; `hardwareCalibrationVerified` remains false. This is expected because the user accepted resetting/redoing calibration.
- Python syntax: 8 files, 0 errors.
- `code.py` SHA-256: `514aa01a36658f59222ba803c6b603137f08b1308d196ac9cc4d7e85296b4fcb`.
- `combined_guard_runtime.py` SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`; normalized runtime size remains 20,200 bytes.
- Calibration position notes remain `(262, 294, 330, 349, 392, 440)`.
- Rhythmic control patterns are present and valid:
  - Start: 4 audible notes, 880 ms total.
  - Stop/HALT: 4 audible notes, 920 ms total.
  - Pause: 3 audible notes, 900 ms total.
  - Resume: 5 audible notes, 900 ms total.
- The old continuous two-second tone constant is absent.
- Record-start `660 Hz / 65 ms`, save-success `880 → 1320 Hz`, retry marker, final-position wrap, Pico-local host `BEEP`, `role=brain`, no real `adafruit_hid` import, no `class Keycode`, internal `Keyboard`, and `release_all()` all passed.

Installation gate is open for controlled copy of `stage14.zip` to `CIRCUITPY`, with `SHA256SUMS.txt` copied last. After reboot, validate Boot/control plane with PING, LUX?, and CALGET before any calibration or Guard/route execution.

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute operational routes, macros, HID actions, or actuators.
- Do not create or copy `ams_key.json`.
- Keep PR #175 Draft; do not merge or release.
- Route serialization and first non-empty-route memory behavior remain separate unapproved gates.
- Do not continue real calibration on the old installed bundle.

## Exact next action

1. Continue from `bermoods/smm` on branch `phase7/light-guard-calibration`.
2. Install validated `stage14.zip` to `CIRCUITPY` with every payload copied first and `SHA256SUMS.txt` copied last.
3. Eject/safely remove the drive, reconnect the board, and validate Boot/control-plane only: PING, LUX?, and CALGET.
4. If Boot/control-plane passes, begin physical calibration from the start with Light Watch off and Guard/route execution still disabled.
5. Do not send `GUARD|ON` or execute routes until calibration is complete and separately validated.
