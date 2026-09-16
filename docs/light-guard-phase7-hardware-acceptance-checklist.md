# Phase 7 Light Guard — Hardware Acceptance Checklist

**Status:** Not run. This checklist is a gate for a separate physical acceptance pass; CI success is not hardware acceptance.

**Firmware:** `pico-light-guard-1.0.0`

**PR:** #175 — keep Open and Draft until this checklist, the app adapter and physical evidence are complete.

## 1. Scope gate

- [ ] Use one regular Raspberry Pi Pico only; do not use Pico W.
- [ ] Record the Pico board identity and the exact firmware package SHA-256 before installation.
- [ ] Do not install this firmware on the existing Phase 6 read-only setup without recording the firmware change and changing the acceptance scope.
- [ ] Keep the Phase 6 `pico-light-readonly` firmware and its wiring unchanged.
- [ ] Do not test or connect Run, Launch, Recovery, Auto Resume, Macro, keyboard, mouse, HID, UART or actuator behavior.
- [ ] Keep PR #175 Draft and do not publish a production release from this pass.

## 2. Approved wiring only

| Part | Connection | Acceptance check |
|---|---|---|
| BH1750/GY-30 SDA | GP20, physical pin 26 | [ ] continuity verified |
| BH1750/GY-30 SCL | GP21, physical pin 27 | [ ] continuity verified |
| BH1750/GY-30 VCC | Pico 3V3 | [ ] 3.3 V only |
| BH1750/GY-30 GND | Pico GND | [ ] common ground verified |
| BH1750/GY-30 ADDR | GND, address 0x23 | [ ] address confirmed |
| Blue square Start/Stop button | GP4 to GND | [ ] pull-up and debounce checked |
| Yellow round Pass/Save button | GP3 to GND | [ ] pull-up and debounce checked |
| Passive piezo | GP6 PWM | [ ] passive piezo only |

**Explicitly prohibited:** Pro Micro, BSS138, UART wiring, HID wiring, keyboard, mouse, motor, relay, actuator, the old integrated buzzer path, or any third button.

## 3. Pre-power checks

- [ ] Inspect for shorts between 3V3 and GND.
- [ ] Confirm GP6 is connected only to the new passive piezo.
- [ ] Confirm GP4 is the blue square button and GP3 is the yellow round button.
- [ ] Confirm no Pro Micro, BSS138, UART or actuator wiring is attached.
- [ ] Confirm the optical sensor is physically fixed and its orientation is documented.
- [ ] Photograph the complete wiring before power-on.

## 4. Firmware and identity

- [ ] Install only the CI-produced `pico-light-guard-1.0.0` package after recording its SHA-256.
- [ ] With no sensor required for boot, send `PING` and capture the complete response.
- [ ] Require an identity equivalent to:

```text
OK|PONG|pico-light-guard 1.0.0|role=light-guard|hid=off|uart=off|actuator=off|...|profiles=6
```

- [ ] Reject the device if role, version family, profile count, HID, UART or actuator declarations do not match.
- [ ] Capture `CALGET` before calibration and record revision and count.
- [ ] Verify Classroom Studio displays the Guard identity and does not treat a Phase 6 read-only identity as a Guard.

## 5. Targeted two-button calibration sequence

The blue button navigates/session-controls. The yellow button starts and saves the selected position.

- [ ] Hold blue GP4 for at least three seconds and confirm entry at `desktop` with its distinct note.
- [ ] Short-press blue GP4 and confirm the next position note; repeat to reach each of the six positions.
- [ ] Confirm that a blue short press at `targeted` does not wrap unexpectedly.
- [ ] At a selected position, press yellow GP3 once and confirm `mode=started` with a five-second window.
- [ ] Keep the sensor fixed for the full five-second sample.
- [ ] Confirm median, spread and tolerance are reported and the position-specific success note plays.
- [ ] Confirm the successful result is not committed until yellow GP3 is pressed a second time.
- [ ] Confirm yellow save emits a saved-stage event and persists only that selected profile.
- [ ] Confirm a blue short press after saving moves to the next position.
- [ ] Confirm a blue short press or blue three-second exit while a successful result is unsaved is rejected and does not discard the result.
- [ ] Hold blue GP4 for three seconds to exit and confirm only yellow-saved positions changed.
- [ ] Repeat a focused repair: navigate directly to `character-dashboard`, sample it, save it with yellow and exit with blue; verify the other five previous values remain unchanged.
- [ ] Verify that an unstable sample is rejected and the same selected position can be retried.
- [ ] Verify that a sensor/I2C failure exits or reports error without replacing the previous saved value.
- [ ] In a separate pass, save all six positions and confirm the complete-set success melody.

Canonical positions, in order:

1. [ ] `desktop`
2. [ ] `login-or-dc`
3. [ ] `character-dashboard`
4. [ ] `entering-game-loading`
5. [ ] `game`
6. [ ] `targeted`

Login and DC must remain one optical calibration record. Any DC ESC behavior is outside this Guard test.

## 6. Classroom Studio synchronization

- [ ] Save/verify the six app-side profiles in Classroom Studio.
- [ ] Confirm Login and DC use the single `login-or-dc` optical record.
- [ ] Capture the app-computed revision.
- [ ] Send six `CALSET` records with the same revision, one per canonical profile.
- [ ] Confirm all six replies are `OK|CALSET|...`.
- [ ] Confirm final `CALGET` reports count 6 and the same revision.
- [ ] Confirm a mismatched or incomplete revision blocks `Guard ON`.
- [ ] Confirm the app adapter displays physical `EVT|CAL` stage, save, exit and retry events.
- [ ] Confirm `GUARD|ON` and `GUARD|OFF` change observation only; no pipeline, RunEngine, HID, keyboard, mouse or actuator action occurs.

## 7. Observation and negative tests

- [ ] With Guard OFF, no stable Guard state event is emitted.
- [ ] With Guard ON and a complete synchronized set, a matching stable state emits one event after `stable-ms`.
- [ ] An ambiguous optical match reports unknown/ambiguous and does not select a profile.
- [ ] A non-matching or stale sensor reading reports unknown/no-match and does not select a profile.
- [ ] Sensor disconnect/I2C failure is visible as an error and does not enable execution.
- [ ] Disable Guard and confirm subsequent state changes do not trigger app actions.
- [ ] Confirm Login/DC remains one optical state; any DC ESC semantics remain outside the Guard firmware and are not tested here.

## 8. Evidence required

- [ ] Firmware package name and SHA-256.
- [ ] Pico identity and board type.
- [ ] Wiring photograph and pin-by-pin verification.
- [ ] Complete serial log including PING, CALGET, blue navigation, yellow start/save, targeted repair, retry/unsaved rejection if tested, six CALSET replies, final CALGET and Guard ON/OFF.
- [ ] Classroom Studio screenshots of identity, revision, six profiles, calibration stage, targeted repair and fail-closed mismatch state.
- [ ] Explicit statement that no execution, HID, UART or actuator behavior was tested or enabled.

## 9. Release gate

Hardware Acceptance is **PASS** only when every applicable item above has evidence, the app adapter and firmware CI checks are green, and a separate reviewer confirms the hardware boundary. Until then, this firmware remains a draft/prerelease test artifact and is not production-ready.
