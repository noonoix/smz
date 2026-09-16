# Portable output architecture

## Principle

Classroom Studio is the authoring kitchen. It edits the seven pipeline tabs, validates the workspace, and builds the files required by the boards. After export, the files copied to the Pico `CIRCUITPY` drive are the runtime source of truth: they determine what the portable system does after boot.

The Windows application must not be required for normal portable execution and must not be treated as a second competing RunEngine for the same Guard transition.

## Desktop Step test boundary

`RunEngine` remains available in Classroom Studio as a manual authoring test tool. It runs the Steps currently written in a selected tab so the author can verify the sequence before export. The existing in-app Run/Stop controls belong to this test boundary only.

Guard events must never consume, hijack or indirectly trigger the Classroom Studio Run/Stop buttons. Guard observation, portable export and desktop Step testing are separate paths:

```text
write/edit Steps -> manual RunEngine test -> approve/export bundle -> copy to CIRCUITPY
```

A successful desktop test does not replace portable-runtime validation and does not make the Windows application a runtime dependency. The desktop application itself does not execute pipeline Steps as a Guard callback.

## Output boundary

A combined portable export is an atomic bundle containing:

- the main `PLAN|2` entry plan;
- one compiled `PLAN|2` file for each canonical visible pipeline tab;
- the `Resumable` plan file;
- the portable plan engine and required runtime modules;
- `guard-transition.json` and `guard-calibration.json`;
- the combined Pico firmware files and `SHA256SUMS.txt`.

Unsupported Steps, missing runtime files, stale revisions and invalid transition mappings must block export before any bundle file is published. A partial bundle is never a valid portable release.

## Combined Guard separation

The combined Phase 7 firmware owns optical observation, ordered transition policy and Portable Step execution on the regular Pico. The Arduino arm remains the mouse/sound component. Pico USB HID remains the keyboard path. The old isolated observation-only firmware is retained only as a historical/diagnostic artifact and must not be confused with the combined runtime contract.

Classroom Studio may display identity, calibration and revision status, but it does not become the Guard execution target. Guard decisions are exported through the manifest and consumed by the portable runtime on the board.

## Approved routing policy

The portable transition manifest encodes:

- ordered stages 1 -> 2 -> 3 -> 4 -> 5;
- DC detection from the shared `login-or-dc` optical profile falling back to stage 2;
- independent Login/DC context in the portable runtime;
- `Targeted` as a side-state with its own Steps and a return to Game;
- one-shot execution until the stable optical state changes;
- fail-closed behavior for missing files, invalid profile/pipeline revisions, ambiguous light state, Stop, or a stale manifest.

`Resumable` is a separate workspace and is not an optical stage.

## Acceptance

A Windows build or a successful Classroom Studio export is not hardware acceptance. Portable acceptance must inspect the exact generated files, verify their hashes, manually copy the approved bundle to the specified Pico only during the separate acceptance pass, and test the approved Pico/Arduino wiring scope for that artifact. Until that pass is run and evidenced, no install, flash, release or acceptance claim is authorized.
