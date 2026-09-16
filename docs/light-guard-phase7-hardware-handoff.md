# Phase 7 Combined Guard — Hardware Handoff Packet

**Status:** Prepared, not run. This document is a human handoff plan only; it does not authorize installation, flashing, physical testing or Hardware Acceptance.

**PR:** #175 — keep Open and Draft.

## Critical package distinction

`firmware/pico-light-guard-1.0.0/` contains **core firmware source only**:

- `code.py`
- `boot.py`
- `combined_guard_runtime.py`
- `guard_calibration_protocol.py`
- documentation and scope metadata

The `pico-light-guard-1.0.0-core` CI artifact is a validation artifact for those sources. **Do not copy it directly to `CIRCUITPY`.** It does not contain the runnable plan, loader, transition module, routes or calibration manifests.

A runnable hardware bundle must be produced by Classroom Studio `PortableGuardBundle.Export`. It must contain, at the bundle root:

```text
code.py
boot.py
plan.txt
plan_engine.py
live_light_guard.py
guard_transition.py
guard_calibration_protocol.py
error_policy.py
combined_guard_runtime.py
desktop_steps.txt
login_or_dc_steps.txt
character_dashboard_steps.txt
entering_game_loading_steps.txt
game_steps.txt
targeted_steps.txt
resumable_steps.txt
guard-transition.json
guard-calibration.json
SHA256SUMS.txt
```

Do not invent missing files or use placeholders. The exact route content and manifests must come from the approved Classroom Studio export.

## 1. Entry conditions

- [ ] A separate physical pass is explicitly approved.
- [ ] The complete Classroom Studio export, not the core artifact, is identified.
- [ ] The complete export hash is recorded; do not use the source commit hash as the bundle hash.
- [ ] A regular Raspberry Pi Pico is available; Pico W is not allowed.
- [ ] The old Phase 6 read-only setup is isolated.
- [ ] A rollback plan and a separate reviewer are assigned.
- [ ] No production release, merge or production-readiness claim is part of the pass.

Until all entry conditions are satisfied, do not connect hardware or copy files to `CIRCUITPY`.

## 2. Approved wiring

| Component | Connection |
|---|---|
| BH1750/GY-30 SDA | Pico GP20, physical pin 26 |
| BH1750/GY-30 SCL | Pico GP21, physical pin 27 |
| BH1750/GY-30 VCC | Pico 3V3 |
| BH1750/GY-30 GND | Pico GND |
| BH1750/GY-30 ADDR | GND, address 0x23 |
| Blue button | GP4 to GND |
| Yellow button | GP3 to GND |
| Passive piezo | GP6 |
| Pico UART0 TX | GP16 -> Arduino RX |
| Pico UART0 RX | GP17 <- Arduino TX |
| Common arm ground | Pico GND <-> Arduino GND |

Arduino remains responsible for mouse/sound. Pico USB HID remains the keyboard path. Do not add Pro Micro, BSS138, relay, old integrated buzzer or unrelated actuator wiring.

## 3. Software-only bundle preparation

1. In Classroom Studio, validate exactly six profiles and seven visible route tabs.
2. Keep the canonical order: `desktop`, `login-or-dc`, `character-dashboard`, `entering-game-loading`, `game`, `targeted`; `Resumable` remains a separate route.
3. Run manual Step tests in Classroom Studio only.
4. Use `PortableGuardBundle.Export` to generate a clean output directory.
5. Verify all files in the complete list above are present at the output root.
6. Verify `SHA256SUMS.txt` contains lowercase SHA-256 digests, two spaces, basenames, every hashed bundle file except itself.
7. Verify manifest/calibration revision parity and the exact seven route map.
8. Record the complete export file list and SHA-256.

The core CI artifact may be used as source evidence, but it must not replace this export.

## 4. Human-operated validation order

Only after the complete export has passed the software checks above:

### A — Power-off inspection

- [ ] Check for shorts between 3V3 and GND.
- [ ] Verify sensor orientation, button colors, UART polarity and common ground.
- [ ] Photograph the complete wiring.

### B — Identity only

- [ ] Use the recorded complete export.
- [ ] Capture `PING` and verify:

```text
OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6
```

- [ ] Capture `CALGET` and record revision/count.
- [ ] Stop if the identity is stale, read-only, isolated or inconsistent.

### C — Calibration

For each profile, in canonical order:

1. Hold GP4 for three seconds while stopped.
2. Press GP3 once to start the five-second sample.
3. Keep the sensor fixed and record median, spread and tolerance.
4. Press GP3 again to save.
5. Confirm unsaved navigation/exit is rejected.
6. Confirm unstable or sensor-failure samples preserve the prior value.

Login and DC remain one optical record: `login-or-dc`.

### D — Classroom Studio synchronization

- [ ] Confirm six app profiles and one shared Login/DC record.
- [ ] Record the app revision.
- [ ] Send six `CALSET` commands with that revision.
- [ ] Record six `OK|CALSET|...` responses.
- [ ] Confirm final `CALGET` reports count 6 and the same revision.

### E — Portable behavior

- [ ] Copy only the complete approved export to `CIRCUITPY`.
- [ ] Verify ordered progression Desktop -> Login/DC -> Character Dashboard -> Entering Game/Loading -> Game.
- [ ] Verify DC fallback, Targeted one-shot return and no repeated route execution.
- [ ] Verify Stop/HALT releases all held arm buttons.
- [ ] Verify missing files, tampering, stale revisions and ambiguous light fail closed.

## 5. Evidence and stop conditions

Record:

```text
complete-export-file-list.txt
complete-export-sha256.txt
pico-board-identity.txt
wiring-photo-before-power.jpg
wiring-pin-check.txt
ping.log
calget-before.log
calibration-events.log
calset-sync.log
calget-after.log
SHA256SUMS.txt
portable-transition.log
halt-release.log
reviewer-signoff.txt
```

Stop and remove power for wrong board/package, wiring uncertainty, unexpected HID/RunEngine/actuator behavior, stale/tampered bundle acceptance, calibration corruption, HALT failure or any need to bypass a fail-closed error.

Hardware Acceptance is **not** passed by CI, the core artifact, a Windows build, a Classroom Studio test or this handoff. It requires the complete export, physical evidence and separate review. Current status remains **Prepared, not run**.
