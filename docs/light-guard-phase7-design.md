# Phase 7 — Light Guard calibration and observation

## Scope

Phase 7 introduces a separate Guard firmware. It does not replace the Phase 6 `pico-light-readonly` firmware and does not authorize an actuator, HID, macro, UART, RunEngine, Launch, Recovery or Auto Resume path.

The Guard observes the BH1750 and reports a stable light profile to Classroom Studio. A later, separately reviewed application change may map that observation to a pipeline context. The firmware itself never selects or executes a pipeline action.

## Hardware boundary

- regular Raspberry Pi Pico, not Pico W;
- BH1750/GY-30: SDA=GP20/pin 26, SCL=GP21/pin 27, VCC=3V3, GND=GND, ADDR=GND/0x23;
- GP4 to GND: Start/Stop; hold for three seconds to enter calibration;
- GP3 to GND: Pass/Next calibration stage;
- passive piezo on GP6 for stage notes and success melody;
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

## Physical calibration flow

1. Hold GP4 for at least three seconds.
2. Pico enters calibration-ready stage 1 and plays the stage-1 note.
3. Press GP3 to start a five-second sample window.
4. The Pico computes median, minimum, maximum and spread.
5. If the spread is too large, the stage is rejected and can be retried.
6. If accepted, the stage center and tolerance are stored and a completion note is played.
7. Press GP3 again to advance to the next stage; the next stage note identifies it.
8. After stage 6, press GP3 once more to persist the complete set and play the success melody.
9. A short GP4 press during calibration cancels without replacing the last complete set.

## App synchronization

Classroom Studio is the source of truth. The app sends one revisioned `CALSET` record per profile:

```text
CALSET|<revision>|<profile-id>|<center>|<tolerance>|<stable-ms>
```

The Pico stores a local copy in `guard-calibration.json`. A revision mismatch is visible and fails closed; the Pico must not silently merge two calibration sets.

## Guard observation

`GUARD|ON` enables observation only. The Pico emits a state event after the matching profile remains stable for its configured duration:

```text
EVT|GUARD|state=<profile-id>|lux=<value>|revision=<revision>
```

No event causes a Pico-side key, mouse, HID, macro or actuator operation. The Classroom Studio adapter must treat `login-or-dc` as a shared optical state and use the active pipeline context to distinguish Login from DC.

## Legacy step policy

`Wait For Light` and `Find Image` remain available for existing Classroom Studio scripts and plans. The new Guard flow does not use them. A later removal would require a separate migration, backup and compatibility review.

## Failure conditions

- unknown or duplicate profile IDs;
- invalid center, tolerance or stable duration;
- unstable five-second sample;
- incomplete six-profile calibration;
- revision mismatch between app and Pico;
- sensor missing, I2C failure or stale observation;
- any attempt to attach execution, HID, UART or actuator behavior.
