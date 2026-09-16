# Portable output architecture

## Principle

Classroom Studio is the authoring kitchen. It edits the seven pipeline tabs, validates the workspace, and builds the files required by the boards. After export, the files copied to the Pico `CIRCUITPY` drive are the runtime source of truth: they determine what the portable system does after boot.

The Windows application must not be required for normal portable execution and must not be treated as a second competing RunEngine for the same Guard transition.

## Desktop Step test boundary

`RunEngine` remains available in Classroom Studio as a manual authoring test tool. It is used to run the Steps currently written in a selected tab so the author can verify the sequence before export. The existing in-app Run/Stop controls belong to this test boundary only.

Guard events must never consume, hijack or indirectly trigger the Classroom Studio Run/Stop buttons. Guard observation, portable export and desktop Step testing are separate paths:

```text
write/edit Steps → manual RunEngine test → approve/export bundle → copy to CIRCUITPY
```

A successful desktop test does not replace portable-runtime validation and does not make the Windows application a runtime dependency.

## Output boundary

A portable pipeline export must be an atomic bundle containing:

- the main `PLAN|2` entry plan;
- one compiled `PLAN|2` file for each canonical visible pipeline tab;
- the `Resumable` plan file;
- the portable plan engine and its required runtime modules;
- the Guard transition/profile manifest and the calibration file required by the selected firmware;
- a README that identifies the target Pico/Arduino wiring, firmware contract and copy location.

Unsupported Steps, missing runtime files, stale revisions and invalid transition mappings must block the export before any bundle file is published. A partial bundle is never a valid portable release.

## Guard separation

The isolated Phase 7 `pico-light-guard` firmware remains a calibration and observation artifact. Its hardware contract is regular Pico + BH1750 + GP4 + GP3 + GP6, with HID/UART/keyboard/mouse/macro/actuator disabled. It reports stable optical states; it does not execute pipeline Steps.

The portable execution firmware/plan bundle is a separate output path. If Guard state routing is added to that path, the routing policy must be encoded in the exported manifest/plan and executed by the portable runtime on the board—not by a desktop callback.

## Approved routing policy

The portable transition manifest must encode:

- ordered stages 1 → 2 → 3 → 4 → 5;
- DC detection from the shared `login-or-dc` optical profile falling back to stage 2;
- independent Login/DC context in the portable runtime;
- `Targeted` as a side-state with its own Steps and a return to Game;
- one-shot execution until the stable optical state changes;
- fail-closed behavior for missing files, invalid profile/pipeline revisions, ambiguous light state, Stop, or a stale manifest.

`Resumable` is a separate workspace and is not an optical stage.

## Acceptance

A Windows build or a successful Classroom Studio export is not hardware acceptance. Portable acceptance must inspect the exact generated files, verify their hashes, boot the specified Pico firmware, and test only the approved board/wiring scope for that artifact.
