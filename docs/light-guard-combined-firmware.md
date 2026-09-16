# Combined Pico Guard + Portable Executor

## Decision

Phase 7 uses one combined firmware on a regular Raspberry Pi Pico. Classroom Studio is the authoring/export kitchen and manual Step-testing environment. After the approved bundle is manually copied to the Pico `CIRCUITPY` drive, the files on that drive are the runtime source of truth.

The Pico owns Guard observation, transition policy and Portable Step execution after the computer disconnects. The existing Arduino arm remains responsible for mouse and sound operations. This is not a desktop RunEngine integration.

## Hardware contract

### Controller Pico

- regular Raspberry Pi Pico, not Pico W;
- BH1750/GY-30: SDA=GP20/physical pin 26, SCL=GP21/physical pin 27, VCC=3V3, GND=GND, ADDR=GND/0x23;
- blue button GP4 to GND;
- yellow button GP3 to GND;
- passive piezo GP6;
- Pico USB HID is the keyboard path for Portable Steps;
- UART0 arm link: GP16 TX -> Arduino RX, GP17 RX <- Arduino TX, common GND, 57600 8N1.

### Arduino arm

The Arduino remains an external portable-runtime component for mouse and sound. The combined Pico firmware keeps framed UART checksums, short-write rejection, acknowledgement pumping, two-move back-pressure, HALT and release-all safety behavior.

## Button modes

### Portable runtime mode

- GP4 short press: Start/Stop the Portable plan engine;
- GP3 short press: Pause/Resume the Portable plan engine;
- GP4 hold for 3 seconds while stopped: enter calibration mode.

### Calibration mode

- GP4 short press: advance to the next optical profile;
- GP4 hold for 3 seconds: exit safely;
- GP3 short press before a sample: start the five-second sample;
- GP3 short press after a successful sample: save the selected profile;
- navigation and exit are rejected while a successful sample is unsaved.

Calibration button events never become runtime Start/Stop or Pause/Resume events.

## Calibration protocol

The six canonical optical profiles are:

```text
desktop
login-or-dc
character-dashboard
entering-game-loading
game
targeted
```

`login-or-dc` is one optical calibration record. Login and DC are distinguished by runtime context, not by a second optical profile.

The shared CircuitPython-safe helper implements:

- `CALGET` for the current revision and calibration profile count;
- exact six-field `CALSET|revision|profile|center|tolerance|stable_ms` parsing;
- allowlisted profile IDs;
- finite, non-negative center/tolerance values;
- non-negative integer stable duration;
- delimiter-safe revision tokens;
- busy-state rejection during plan execution or physical calibration.

Physical calibration uses a five-second sample, median/spread gate and explicit save confirmation. Local physical saves use the temporary revision `pending`; Classroom Studio later publishes the final app revision through `CALSET`.

## Portable behavior

The Pico loads the exported entry plan, seven route files, plan engine, Guard calibration and transition manifest from `CIRCUITPY`. Classroom Studio is not required after the bundle is copied.

The runtime implements:

- ordered stages Desktop -> Login/DC -> Character Dashboard -> Entering Game/Loading -> Game;
- DC fallback from active stages and Targeted to stage 2;
- Targeted as a side-state with its own Steps and a fresh Game return observation;
- one-shot execution until the stable optical state changes;
- fail-closed behavior for ambiguous light, missing route, stale calibration, stale manifest or missing runtime files;
- Stop/HALT that aborts the plan and safely releases the Arduino arm.

## Exported bundle

A valid combined export contains:

- `code.py` and `boot.py`;
- `plan.txt` and the seven canonical route files;
- `plan_engine.py` and required portable runtime modules;
- `guard-calibration.json` and `guard-transition.json`;
- `SHA256SUMS.txt`.

The exporter validates the workspace, six profiles, route map and revision consistency before publishing. A partial or stale bundle is rejected by the portable loader before route use.

## Desktop boundary

RunEngine remains a Classroom Studio authoring test tool for the selected tab. The flow is:

```text
write/edit Steps -> manually test with RunEngine -> approve/export bundle -> copy files to CIRCUITPY
```

Guard events do not invoke, consume, hijack or indirectly trigger the desktop Run/Stop controls. A successful desktop test is not Portable or hardware acceptance and does not create a Windows runtime dependency.

## Safety and acceptance boundary

The old isolated observation-only package is not the runtime source of truth for this combined contract. No firmware is to be installed on the existing setup while the separate combined-hardware acceptance pass is incomplete.

CI, syntax/package validation and Windows build success are prerequisites only. Hardware acceptance requires the exact combined package SHA, approved wiring evidence, calibration/synchronization logs, portable route/transition evidence and a separate reviewer. Until that pass is explicitly completed, PR #175 remains Draft and no hardware acceptance or production-readiness claim may be made.
