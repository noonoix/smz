# Phase 7 handoff — 2026-09-17

## Synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records technical checkpoints, evidence, hashes, safety gates, fixes, and exact next actions. The full chat transcript is intentionally not copied. This file stays on `docs/session-2026-09-17-handoff` so documentation commits do not alter code-artifact provenance.

## Current state

- Active repository: `bermoods/smm`
- Original repository mirror source: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Old Draft PR: https://github.com/c4haztex/smc-1/pull/175 (PR metadata itself was not migrated; branch content was mirrored.)
- Last validated pre-migration code head: `388bc0551bb9196dcf2a2933b45d7f3d33ccbac3`
- Latest active branch head after rescue cleanup: `3c97560ea0f0200543d4e9abd68d5100fb7e5f79`
- Latest functional code change: `2c2a9c8700ba617d6431b2b8410e4bb17765811c`
- Current Windows artifact run before migration: https://github.com/c4haztex/smc-1/actions/runs/35261951361
- CI: new Draft PR #3 on `bermoods/smm` completed successfully: 12 executable checks succeeded; downloadable package skipped by branch condition.
- Current Windows artifact run after migration: https://github.com/bermoods/smm/actions/runs/35281421528
- Installed hardware bundle remains `stage12`; it does not contain the latest calibration/control-audio changes.
- Board: COM30/COM31 hot-plug detected; COM31 automatically selected; `role=brain` confirmed.
- Hardware passed: Boot, control plane, compact light telemetry, `SETRES`, live Buzzer Step, calibration-entry cue, and stable Desktop sample-complete cue.
- Next package: download the new Windows artifact from run `35281421528`, export Combined Portable Guard, and validate a fresh `stage14.zip`.

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

## New repository PR and CI

A new Draft PR was created on the migrated repository so Phase 7 remains reviewable and CI-backed.

- Draft PR: https://github.com/bermoods/smm/pull/3
- Head: `3c97560ea0f0200543d4e9abd68d5100fb7e5f79`
- CI run family: https://github.com/bermoods/smm/actions/runs/35281421528
- Result: 12 executable checks succeeded.
- `autocycle / downloadable test package` was skipped by the existing branch condition, as before.

The next hardware package must be produced from this migrated repository artifact, not from the old `c4haztex/smc-1` run.

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

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute operational routes, macros, HID actions, or actuators.
- Do not create or copy `ams_key.json`.
- Keep PR #175 Draft; do not merge or release.
- Route serialization and first non-empty-route memory behavior remain separate unapproved gates.
- Do not continue real calibration on the old installed bundle.

## Exact next action

1. Continue from `bermoods/smm` on branch `phase7/light-guard-calibration`.
2. Download `light-state-windows-output` from the new repository run `35281421528`.
3. Extract into a completely new Windows folder and launch that build.
4. Export Combined Portable Guard into a clean staging folder and send the resulting archive with a new name such as `stage14.zip` for provenance and content validation.
5. Do not copy anything to `CIRCUITPY`, do not send `GUARD|ON`, and do not continue hardware calibration until validation passes.
