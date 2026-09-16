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
- [ ] Do not merge PR #174 or #175 and do not publish a production release from this pass.

## 2. Approved wiring only

| Part | Connection | Acceptance check |
|---|---|---|
| BH1750/GY-30 SDA | GP20, physical pin 26 | [ ] continuity verified |
| BH1750/GY-30 SCL | GP21, physical pin 27 | [ ] continuity verified |
| BH1750/GY-30 VCC | Pico 3V3 | [ ] 3.3 V only |
| BH1750/GY-30 GND | Pico GND | [ ] common ground verified |
| BH1750/GY-30 ADDR | GND, address 0x23 | [ ] address confirmed |
| Start/Stop button | GP4 to GND | [ ] pull-up and debounce checked |
| Pass/Next button | GP3 to GND | [ ] pull-up and debounce checked |
| Passive piezo | GP6 PWM | [ ] passive piezo only |

**Explicitly prohibited:** Pro Micro, BSS138, UART wiring, HID wiring, keyboard, mouse, motor, relay, actuator, the old integrated buzzer path, or any third button.

## 3. Pre-power checks

- [ ] Inspect for shorts between 3V3 and GND.
- [ ] Confirm GP6 is connected only to the new passive piezo.
- [ ] Confirm GP4 and GP3 are the only physical buttons.
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

## 5. Physical calibration sequence

For each of the six positions, record the physical scene, timestamp, stage event and result:

1. [ ] `desktop`
2. [ ] `login-or-dc`
3. [ ] `character-dashboard`
4. [ ] `entering-game-loading`
5. [ ] `game`
6. [ ] `targeted`

For every stage:

- [ ] Hold GP4 for at least three seconds to enter calibration-ready stage 1.
- [ ] Confirm the distinct stage note and `EVT|CAL|mode=ready` event.
- [ ] Press GP3 once and confirm `mode=started` with a five-second window.
- [ ] Keep the sensor fixed for the full five-second sample.
- [ ] Confirm median, spread and tolerance are reported.
- [ ] Confirm an unstable sample is rejected and the stage can be retried without silently replacing the last complete set.
- [ ] Press GP3 after a successful stage and confirm the next stage note and profile ID.
- [ ] After stage 6, press GP3 once more and confirm `mode=complete`, count 6 and the success melody.
- [ ] Confirm a short GP4 press during calibration cancels and preserves the last complete set.

## 6. Classroom Studio synchronization

- [ ] Save/verify the six app-side profiles in Classroom Studio.
- [ ] Confirm Login and DC use the single `login-or-dc` optical record.
- [ ] Capture the app-computed revision.
- [ ] Send six `CALSET` records with the same revision, one per canonical profile.
- [ ] Confirm all six replies are `OK|CALSET|...`.
- [ ] Confirm final `CALGET` reports count 6 and the same revision.
- [ ] Confirm a mismatched or incomplete revision blocks `Guard ON`.
- [ ] Confirm the app adapter displays physical `EVT|CAL` events and Guard state events.
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
- [ ] Complete serial log including PING, CALGET, all six stages, retries/cancel if tested, six CALSET replies, final CALGET and Guard ON/OFF.
- [ ] Classroom Studio screenshots of identity, revision, six profiles, calibration stage and fail-closed mismatch state.
- [ ] Explicit statement that no execution, HID, UART or actuator behavior was tested or enabled.

## 9. Release gate

Hardware Acceptance is **PASS** only when every applicable item above has evidence, the app adapter and firmware CI checks are green, and a separate reviewer confirms the hardware boundary. Until then, this firmware remains a draft/prerelease test artifact and is not production-ready.
