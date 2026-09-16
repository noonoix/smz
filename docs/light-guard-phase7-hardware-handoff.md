# Phase 7 Combined Guard — Hardware Handoff Packet

**Status:** Prepared, not run. This document is a handoff plan only; it does not authorize installation, flashing, physical testing or Hardware Acceptance.

**PR:** #175 — keep Open and Draft.

**Firmware line:** `pico-light-guard-1.0.0`

**Current software evidence:** CI passed on the PR head. Record the exact CI artifact SHA-256 immediately before any future physical pass; do not infer or substitute a source-commit hash.

## 1. Entry conditions

A separate reviewer must confirm all of the following before any power is applied:

- [ ] The physical pass is explicitly approved as a separate activity.
- [ ] The exact CI-produced combined package and SHA-256 are recorded.
- [ ] A regular Raspberry Pi Pico is available; Pico W is not allowed.
- [ ] The existing Phase 6 read-only setup is isolated and will not be modified.
- [ ] The rollback plan is written: disconnect power, remove the combined bundle, restore the prior read-only setup only through its own approved procedure.
- [ ] No production release, merge or production-readiness claim is part of the pass.
- [ ] A reviewer is assigned to observe and record evidence.

Until every entry condition is checked, stop at software/CI evidence. Do not connect hardware.

## 2. Approved wiring record

Record the actual wiring and photographs in the acceptance evidence log. Only this boundary is in scope:

| Component | Connection | Record before power-on |
|---|---|---|
| BH1750/GY-30 SDA | Pico GP20, physical pin 26 | continuity and photo |
| BH1750/GY-30 SCL | Pico GP21, physical pin 27 | continuity and photo |
| BH1750/GY-30 VCC | Pico 3V3 | 3.3 V confirmation |
| BH1750/GY-30 GND | Pico GND | common-ground confirmation |
| BH1750/GY-30 ADDR | GND, address 0x23 | address confirmation |
| Blue button | GP4 to GND | pull-up and debounce |
| Yellow button | GP3 to GND | pull-up and debounce |
| Passive piezo | GP6 | passive piezo confirmation |
| Pico UART0 TX | GP16 -> Arduino RX | 57600 8N1 |
| Pico UART0 RX | GP17 <- Arduino TX | 57600 8N1 |
| Arduino arm ground | Pico GND <-> Arduino GND | common-ground confirmation |

The Arduino arm remains the mouse/sound component. Pico USB HID remains the keyboard path. Do not add Pro Micro, BSS138, relay, old integrated buzzer or unrelated actuator wiring.

## 3. Staged validation order

Do not skip a stage or combine evidence from different packages.

### Stage A — Power-off inspection

- [ ] Inspect for shorts between 3V3 and GND.
- [ ] Verify sensor orientation and fixed mounting.
- [ ] Verify button colors and pin mapping.
- [ ] Verify UART polarity, baud and common ground.
- [ ] Photograph the complete wiring.

### Stage B — Identity only

- [ ] Install/use only the recorded CI package during the approved pass.
- [ ] Capture `PING` and verify:

```text
OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6
```

- [ ] Capture `CALGET` and record revision/count.
- [ ] Stop immediately if the identity is read-only, isolated, stale or inconsistent with the package record.

### Stage C — Calibration protocol

For each canonical profile, record the raw event log:

1. Hold GP4 for three seconds while stopped to enter calibration.
2. Use GP4 to select, in order: `desktop`, `login-or-dc`, `character-dashboard`, `entering-game-loading`, `game`, `targeted`.
3. Press GP3 once to start the five-second sample.
4. Keep the sensor fixed; record median, spread and tolerance.
5. Press GP3 again to save.
6. Confirm unsaved navigation/exit is rejected.
7. Confirm an unstable or sensor-failure sample preserves the previous saved value.
8. Exit with a three-second GP4 hold and record the saved profile set.

Login and DC must remain one optical calibration record: `login-or-dc`.

### Stage D — Classroom Studio synchronization

- [ ] Confirm exactly six profiles in the app.
- [ ] Record the app-computed revision.
- [ ] Send one `CALSET` per canonical profile with that revision.
- [ ] Record six `OK|CALSET|...` replies.
- [ ] Confirm final `CALGET` reports count 6 and the same revision.
- [ ] Verify stale, incomplete or mismatched revisions fail closed.
- [ ] Verify calibration events never become runtime Start/Stop or Pause/Resume events.

### Stage E — Export and portable execution

- [ ] Export after manual Step testing and record the exact bundle file list.
- [ ] Verify the seven route files, `plan.txt`, runtime modules, both JSON files and `SHA256SUMS.txt`.
- [ ] Verify the manifest hash set covers every hashed bundle file and excludes `SHA256SUMS.txt` itself.
- [ ] Manually copy the approved bundle to `CIRCUITPY`; do not depend on Windows after disconnect.
- [ ] Verify ordered progression: Desktop -> Login/DC -> Character Dashboard -> Entering Game/Loading -> Game.
- [ ] Verify DC fallback, Targeted one-shot behavior and fresh Game return without replaying Game Steps.
- [ ] Verify Stop/HALT releases all held arm buttons.
- [ ] Verify missing files, tampering, stale revision and ambiguous light fail closed.

## 4. Evidence packet template

Create one evidence folder outside the firmware bundle containing:

```text
package-name.txt
package-sha256.txt
pico-board-identity.txt
wiring-photo-before-power.jpg
wiring-pin-check.txt
ping.log
calget-before.log
calibration-events.log
calset-sync.log
calget-after.log
bundle-file-list.txt
SHA256SUMS.txt
portable-transition.log
halt-release.log
reviewer-signoff.txt
```

`reviewer-signoff.txt` must state the package SHA, board type, wiring scope, observed negative tests and whether every applicable checklist item has evidence. It must not say Hardware Acceptance passed unless the separate acceptance gate is actually completed.

## 5. Stop and rollback triggers

Stop the pass and remove power if any of the following occurs:

- wrong Pico type, unexpected board identity or wrong package SHA;
- 3V3/GND short, wrong voltage or uncertain UART polarity;
- unexpected HID, desktop RunEngine, Windows-runtime or actuator behavior;
- stale/tampered bundle accepted by the loader;
- calibration save changes an unrelated profile or cannot reload;
- Stop/HALT fails to release the arm;
- any test requires bypassing a fail-closed error.

After a stop, preserve logs and photographs. Do not retry by changing firmware files manually.

## 6. Exit gate

This handoff is complete only when a separate reviewer has the evidence packet and has explicitly recorded one of:

- **Not started:** software/CI evidence only; no hardware was connected.
- **Blocked:** a listed entry or negative test failed; no acceptance claim.
- **Accepted for the separate pass:** all applicable evidence is present and the reviewer authorizes the next controlled step.
- **Hardware Acceptance:** only if every applicable item in `docs/light-guard-phase7-hardware-acceptance-checklist.md` has been physically evidenced and reviewed.

The current state remains **Prepared, not run**. CI success, a Windows build, a Classroom Studio test or this handoff document are not Hardware Acceptance and do not authorize release or production use.
