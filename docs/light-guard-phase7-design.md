# Phase 7 — Light Guard calibration and observation

## Scope

Phase 7 introduces a separate Guard firmware. It does not replace the Phase 6 `pico-light-readonly` firmware and does not authorize an actuator, HID, macro, UART, RunEngine, Launch, Recovery or Auto Resume path.

The Guard observes the BH1750 and reports a stable light profile to Classroom Studio. A later, separately reviewed application change may map that observation to a pipeline context. The firmware itself never selects or executes a pipeline action.

## Hardware boundary

- regular Raspberry Pi Pico, not Pico W;
- BH1750/GY-30: SDA=GP20/pin 26, SCL=GP21/pin 27, VCC=3V3, GND=GND, ADDR=GND/0x23;
- blue square GP4 to GND: Start/Stop; hold for three seconds to enter or exit calibration;
- yellow round GP3 to GND: Pass/Save;
- passive piezo on GP6 for position notes, stage-success notes and the complete-set melody;
- no Pro Micro, BSS138, UART, HID, keyboard, mouse, macro, motor, relay or actuator.

GP6 is allowed only in this new isolated Guard firmware. It must not be added to the Phase 6 read-only firmware or connected as the old integrated buzzer path.

## Six light profiles

There are six optical profiles:

1. `desktop`
2. `login-or-dc`
3. `character-dashboard`
4. `entering-game-loading`
5. `game`
6. `targeted`

Login and DC intentionally share one optical profile. Their difference is an application/pipeline action: DC has its own ESC behavior. The profile is not split into two optical calibration records.

## Two-button partial calibration flow

The two physical buttons have separate responsibilities:

- **Blue square / GP4 — navigation and session control**
  - hold for 3 seconds outside calibration: enter at position 1;
  - short press during calibration: move to the next of the six positions;
  - hold for 3 seconds during calibration: exit safely;
  - short press outside calibration: toggle Guard observation.
- **Yellow round / GP3 — sample and save**
  - short press when the selected position is ready: start the five-second sample;
  - short press after a successful sample: save the selected position locally.

The position note plays whenever a position is entered. The five-second sample uses median and spread/stability gating. A successful sample plays that position's completion note but is not committed until the yellow button is pressed. A blue navigation press or blue long-hold is rejected while an unsaved successful sample is pending, so a result cannot be lost accidentally.

The flow supports a targeted repair instead of forcing a full six-position recalibration:

1. Hold blue GP4 for three seconds to enter at `desktop`.
2. Short-press blue until the damaged position, for example `character-dashboard`, is announced by its distinct note.
3. Press yellow GP3 to start the five-second sample.
4. When the sample succeeds and the completion note plays, press yellow again to save that position.
5. Hold blue GP4 for three seconds to exit. Only positions saved with yellow are changed; the other five retain their previous values.

If all six positions are saved during one session, the success melody for the complete set also plays. Classroom Studio remains the source of truth and must later synchronize its six records with one revision.

## App synchronization

Classroom Studio is the source of truth. The app sends one revisioned `CALSET` record per profile:

```text
CALSET|<revision>|<profile-id>|<center>|<tolerance>|<stable-ms>
```

The Pico stores a local copy in `guard-calibration.json`. A revision mismatch is visible and fails closed; the Pico must not silently merge two calibration sets.

The Classroom Studio Phase 7 adapter provides a visible Guard panel with:

- Guard identity and six-profile validation from `PING`;
- `CALGET` revision/count display;
- app-side deterministic revision derived from the six canonical profiles;
- sequential upload and final verification of all six `CALSET` records;
- physical `EVT|CAL` stage/retry/save/exit display;
- Guard state and enabled/disabled observation display.

`Guard ON` is fail-closed until the current session has uploaded and verified all six records with one revision. Saving the app-side light profiles invalidates that trust and requires a fresh sync.

## Guard observation

`GUARD|ON` enables observation only. The Pico emits a state event after the matching profile remains stable for its configured duration:

```text
EVT|GUARD|state=<profile-id>|lux=<value>|revision=<revision>
```

No event causes a Pico-side key, mouse, HID, macro or actuator operation. The Classroom Studio adapter must treat `login-or-dc` as a shared optical state and use the active pipeline context to distinguish Login from DC.

## Legacy step policy

`Wait For Light` and `Find Image` remain available for existing Classroom Studio scripts and plans. The new Guard flow does not use them. A later removal would require a separate migration, backup and compatibility review.

## Hardware acceptance

Physical testing is not yet accepted. Use [`light-guard-phase7-hardware-acceptance-checklist.md`](./light-guard-phase7-hardware-acceptance-checklist.md) for the isolated wiring, firmware identity, targeted/partial calibration, synchronization, negative tests and required evidence. The checklist explicitly prohibits the Phase 6 wiring, Pro Micro, BSS138, UART, HID and actuator paths.

## Failure conditions

- unknown or duplicate profile IDs;
- invalid center, tolerance or stable duration;
- unstable five-second sample;
- unsaved successful sample being skipped;
- incomplete six-profile calibration;
- revision mismatch between app and Pico;
- sensor missing, I2C failure or stale observation;
- any attempt to attach execution, HID, UART or actuator behavior.
