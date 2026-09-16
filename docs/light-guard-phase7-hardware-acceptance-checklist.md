# Phase 7 Combined Guard + Portable Executor — Hardware Acceptance Checklist

**Status:** Not run. This checklist is a gate for a separate physical acceptance pass; CI success and a Windows export are not hardware acceptance.

**Firmware:** `pico-light-guard-1.0.0` combined runtime

**PR:** #175 — keep Open and Draft until the combined checklist, exact package evidence and physical review are complete.

## 1. Scope gate

- [ ] Use one regular Raspberry Pi Pico only; do not use Pico W.
- [ ] Record the Pico board identity and exact CI package SHA-256 before any installation.
- [ ] Do not install or flash this package on the existing Phase 6 read-only setup.
- [ ] Keep the Phase 6 read-only firmware and its wiring/evidence separate from this combined acceptance.
- [ ] Do not treat Classroom Studio RunEngine success as portable or hardware acceptance.
- [ ] Keep PR #175 Draft and do not publish a production release from this pass.
- [ ] No physical test is considered started until the package SHA, wiring and rollback plan are recorded.

## 2. Approved combined wiring only

| Part | Connection | Acceptance check |
|---|---|---|
| BH1750/GY-30 SDA | GP20, physical pin 26 | [ ] continuity verified |
| BH1750/GY-30 SCL | GP21, physical pin 27 | [ ] continuity verified |
| BH1750/GY-30 VCC | Pico 3V3 | [ ] 3.3 V only |
| BH1750/GY-30 GND | Pico GND | [ ] common ground verified |
| BH1750/GY-30 ADDR | GND, address 0x23 | [ ] address confirmed |
| Blue Start/Stop/calibration button | GP4 to GND | [ ] pull-up and debounce checked |
| Yellow Pause/Resume/save button | GP3 to GND | [ ] pull-up and debounce checked |
| Passive piezo | GP6 PWM | [ ] passive piezo only |
| Pico UART0 TX | GP16 -> Arduino RX | [ ] 57600 8N1 verified |
| Pico UART0 RX | GP17 <- Arduino TX | [ ] 57600 8N1 verified |
| Common arm ground | Pico GND <-> Arduino GND | [ ] common ground verified |

**The Arduino arm remains responsible for mouse and sound.** No Pro Micro, BSS138, relay or unrelated actuator wiring is allowed. The old isolated read-only firmware must not be mixed with this wiring.

## 3. Pre-power checks

- [ ] Inspect for shorts between 3V3 and GND.
- [ ] Confirm GP6 is connected only to the new passive piezo.
- [ ] Confirm GP4 is blue and GP3 is yellow.
- [ ] Confirm UART polarity, common ground and `57600 8N1`.
- [ ] Confirm no Pico W, Pro Micro, BSS138 or old integrated buzzer path is attached.
- [ ] Confirm the optical sensor is fixed and its orientation is documented.
- [ ] Photograph the complete Pico + BH1750 + buttons + piezo + Arduino-arm wiring before power-on.

## 4. Firmware and identity

- [ ] Install only the CI-produced combined package after recording its SHA-256.
- [ ] Capture the complete `PING` response:

```text
OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6
```

- [ ] Reject the device if it identifies as the old read-only or isolated role.
- [ ] Capture `CALGET` before calibration and record revision and count.
- [ ] Confirm the package contains the combined runtime, helper, manifest/calibration loaders and route files.
- [ ] Confirm Classroom Studio displays the combined identity/revision and does not make the Windows application the runtime target.

## 5. Two-button calibration sequence

The button meanings are mode-dependent: GP4 controls runtime Start/Stop or calibration navigation; GP3 controls runtime Pause/Resume or calibration sample/save.

- [ ] With the plan stopped, hold GP4 for at least three seconds and confirm calibration starts at `desktop`.
- [ ] Short-press GP4 and confirm navigation through all six profiles; GP4 at `targeted` does not wrap.
- [ ] At a selected profile, press GP3 once and confirm `mode=started` with a five-second window.
- [ ] Keep the sensor fixed for the full sample.
- [ ] Confirm median, spread and tolerance are reported.
- [ ] Confirm a successful result is not committed until GP3 is pressed a second time.
- [ ] Confirm GP3 save emits a saved-stage event and changes only that profile.
- [ ] Confirm GP4 navigation or three-second exit is rejected while a successful result is unsaved.
- [ ] Hold GP4 for three seconds to exit and confirm only GP3-saved profiles changed.
- [ ] Repeat a focused repair at `character-dashboard`; verify the other five values remain unchanged.
- [ ] Verify an unstable sample can be retried without replacing the previous value.
- [ ] Verify a sensor/I2C failure reports an error and preserves the previous saved value.
- [ ] Separately save all six profiles and confirm the complete-set success indication.

Canonical positions, in order:

1. [ ] `desktop`
2. [ ] `login-or-dc`
3. [ ] `character-dashboard`
4. [ ] `entering-game-loading`
5. [ ] `game`
6. [ ] `targeted`

Login and DC remain one optical calibration record. Any DC action semantics are exercised through the portable transition tests below, not a second optical profile.

## 6. Classroom Studio synchronization

- [ ] Verify exactly six app-side profiles in Classroom Studio.
- [ ] Confirm Login and DC use the single `login-or-dc` record.
- [ ] Capture the app-computed revision.
- [ ] Send one `CALSET` for each canonical profile with the same revision.
- [ ] Confirm all six replies are `OK|CALSET|...`.
- [ ] Confirm final `CALGET` reports count 6 and the same revision.
- [ ] Confirm a mismatched, incomplete or stale revision blocks the combined Guard plan.
- [ ] Confirm the app adapter displays physical `EVT|CAL` ready, sample, complete, save, exit and retry events.
- [ ] Confirm calibration events never become runtime Start/Stop or Pause/Resume actions.

## 7. Portable bundle and transition tests

- [ ] Export from Classroom Studio after manual Step testing; record the export hashes.
- [ ] Verify the exact seven route files, `plan.txt`, runtime modules, `guard-transition.json`, `guard-calibration.json` and `SHA256SUMS.txt` are present.
- [ ] Manually copy the approved files to the Pico `CIRCUITPY` drive; do not depend on the Windows application after disconnect.
- [ ] Confirm GP4 short press starts/stops the portable plan and GP3 short press pauses/resumes it only outside calibration.
- [ ] Confirm ordered progression is Desktop -> Login/DC -> Character Dashboard -> Entering Game/Loading -> Game.
- [ ] Confirm repeated stable optical readings execute each route only once.
- [ ] Confirm DC from active stages and Targeted falls back to stage 2, then recovers in order.
- [ ] Confirm Targeted executes once and returns to Game after a fresh stable Game observation without replaying Game Steps.
- [ ] Confirm missing route, stale manifest, stale calibration, ambiguous light and invalid revision fail closed.
- [ ] Confirm Stop/HALT aborts the plan and releases all held arm buttons.

## 8. HID, Arduino arm and negative tests

- [ ] Verify Portable keyboard Steps use Pico USB HID only after the portable bundle is running.
- [ ] Verify mouse and sound Steps use the Arduino arm through framed UART acknowledgements.
- [ ] Verify arm back-pressure, short-write rejection, HALT and release-all behavior.
- [ ] Verify piezo output is passive GP6 only.
- [ ] Verify no Guard event invokes Classroom Studio RunEngine or desktop Run/Stop controls.
- [ ] With Guard/runtime stopped, no route or actuator action occurs.
- [ ] Disconnect BH1750 or invalidate the bundle and confirm fail-closed behavior without executing a stale route.
- [ ] Disconnect the computer and confirm the Pico continues only from the copied `CIRCUITPY` files.

## 9. Evidence required

- [ ] Firmware package name and SHA-256.
- [ ] Pico identity, board type and wiring photograph.
- [ ] Pin-by-pin verification including UART and common ground.
- [ ] Complete serial log including PING, CALGET, calibration navigation/start/save, retry/unsaved rejection, six CALSET replies, final CALGET, Guard ON/OFF and HALT.
- [ ] Classroom Studio screenshots of identity, revision, six profiles, calibration events and fail-closed mismatch state.
- [ ] Exported bundle file list and `SHA256SUMS.txt`.
- [ ] Portable transition log covering ordered recovery, DC fallback, Targeted return and one-shot behavior.
- [ ] Explicit statement that no production release or unrelated hardware was used.

## 10. Release gate

Hardware Acceptance is **PASS** only when every applicable item above has evidence and a separate reviewer confirms the combined Pico/Arduino boundary. Until then, this firmware remains a Draft/prerelease test artifact. No release, merge, installation, flash or production-acceptance claim is authorized.
