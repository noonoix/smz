# Combined Pico Guard + Portable Executor

## Decision

The current isolated `pico-light-guard` firmware will be replaced by one combined firmware on a regular Raspberry Pi Pico. The existing Arduino arm remains responsible for mouse and sound operations.

This is a new firmware contract. It is not the old Phase 7 observation-only acceptance scope.

## Hardware

### Controller Pico

- regular Raspberry Pi Pico, not Pico W;
- BH1750/GY-30: SDA=GP20/pin 26, SCL=GP21/pin 27, VCC=3V3, GND=GND, ADDR=GND/0x23;
- blue button GP4 to GND;
- yellow button GP3 to GND;
- passive piezo GP6;
- Pico USB HID remains the keyboard path for portable Steps;
- UART0 arm link: GP16 TX -> Arduino RX, GP17 RX <- Arduino TX, common GND, 57600 8N1.

### Arduino arm

The Arduino remains an external portable-runtime component for mouse and sound. The combined Pico firmware must keep the existing framed UART, acknowledgement, back-pressure and stop/release protections.

## Button modes

The same two buttons have mode-dependent responsibilities:

### Portable runtime mode

- GP4 short press: Start/Stop the portable plan engine;
- GP3 short press: Pause/Resume the portable plan engine;
- GP4 hold for 3 seconds: enter calibration mode when the engine is stopped.

### Calibration mode

- GP4 short press: advance to the next optical position;
- GP4 hold for 3 seconds: exit safely;
- GP3 short press before a sample: start the five-second sample;
- GP3 short press after a successful sample: save the selected position;
- navigation or exit is rejected while a successful sample is unsaved.

The firmware must never interpret a calibration button event as a runtime Start/Stop or Pause/Resume event.

## Portable behavior

The Pico loads the exported `plan.txt`, tab plan files, portable runtime modules, Guard calibration and transition manifest from `CIRCUITPY`. Classroom Studio is not required after the bundle is copied.

The runtime must implement:

- ordered stages 1 -> 2 -> 3 -> 4 -> 5;
- shared `login-or-dc` optical calibration with independent Login/DC context;
- DC fallback from active in-game stages to stage 2;
- Targeted as a side-state with its own Steps and return to Game;
- one-shot transition execution until the stable optical state changes;
- fresh stable-state rearming;
- Stop that aborts the plan and releases the Arduino arm safely;
- fail-closed behavior for ambiguous light, missing route, stale calibration, stale bundle revision or missing runtime files.

## Exported bundle

A valid portable export must atomically contain:

- `code.py`;
- `boot.py`;
- `plan.txt`;
- one compiled PLAN|2 file for each visible tab;
- `plan_engine.py` and required runtime modules;
- `guard-calibration.json`;
- `guard-transition.json`;
- `README-FLASH.md`;
- `SHA256SUMS.txt`.

The exported files, not the Windows application, are the runtime source of truth.

## Safety boundary

The old isolated Guard firmware and its no-HID/no-UART hardware acceptance checklist are not evidence for this combined firmware. Direct replacement is authorized only after portable simulator tests, export-contract tests, Windows build validation, firmware syntax/package validation and a new combined-hardware acceptance pass.

No firmware is to be installed on the existing setup while this contract is incomplete. The PR remains Draft.
