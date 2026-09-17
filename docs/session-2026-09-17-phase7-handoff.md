# Phase 7 handoff — 2026-09-17

## Purpose and synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records the technical checkpoint, decisions, evidence, hashes, safety gates, failures, fixes, and exact next action. The full chat transcript is intentionally not copied.

Every substantive Notion checkpoint is mirrored here on the dedicated `docs/session-2026-09-17-handoff` branch so documentation commits do not change artifact provenance on the code branch.

## Current state

- Repository: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Draft PR: https://github.com/c4haztex/smc-1/pull/175
- Current validated code head: `79b4618700bd5a275d6241363d1e00ba43573184`
- PR remains open and Draft; do not merge or release.
- CI for the current head: 12 executable checks succeeded; downloadable test package skipped by branch condition.
- Current Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35252986013
- Installed hardware bundle: `stage12`
- Board auto-detection: COM30/COM31 discovered after hot-plug; data/control port automatically selected as COM31.
- Board identity: `combined-pico-guard-executor|hid=on|uart=on|profiles=6|role=brain`.
- Boot, control plane, compact light telemetry, `SETRES`, and live Buzzer Step have passed on hardware.
- Active phase: verify calibration-entry audio, then perform controlled six-profile calibration one profile at a time.

## Fixed wiring and interaction contract

- BH1750/GY-30: 3V3, GND, SDA=GP20, SCL=GP21, address `0x23`.
- GP4 blue square button: Start/Stop; hold to enter/exit calibration. Inside calibration it advances positions only when explicitly instructed.
- GP3 yellow round button: maintenance gate when held during boot; sample/save inside calibration.
- GP6: passive piezo.
- UART0 to arm: GP16 TX, GP17 RX, 57600 8N1, common ground.
- Current board ports: COM30/COM31; COM31 is the verified data/control port.

## Canonical calibration profiles and tones

1. `desktop` — 262 Hz
2. `login-or-dc` — 294 Hz
3. `character-dashboard` — 330 Hz
4. `entering-game-loading` — 349 Hz
5. `game` — 392 Hz
6. `targeted` — 440 Hz

The blue button moves between positions. The yellow button starts sampling and saves only after sampling completes. Each physical sample lasts five seconds. The runtime uses median center, rejects fewer than five readings or spread greater than 5 lux, computes tolerance as `max(2.0, spread * 1.5)`, and uses `stable_ms=750`.

## Durable code fixes

| Commit | Change |
|---|---|
| `0767c6fffdc89741db8a99b36494aa6ad6049949` | Corrected Combined Guard README/metadata and enforced the complete 21-file inventory. |
| `df94be8ecaf986feb7160dabb2930dde06ab185f` | Corrected Bridge identity handling while preserving fail-closed behavior. |
| `fd63358bcbbf54a761c1df3e1cdafcff5d85ea3d` | Changed early import order after the first hardware MemoryError. |
| `8ddf5d7a006688d729eb129b2bb1a324f30f9f75` | Deferred the large plan engine until actual route execution. |
| `a8cf753bd93fa7055b493f3fced7dfcb0478eb73` | Preserved the workflow entrypoint contract after bundle-first loading. |
| `3abf5f9898864e4c6290872106ce6d00aa7afe12` | Parsed the bundle on a fresh heap and reused the parsed result. |
| `bad1e2a70dec761aa32b19bc6d428134dd4e8acf` | Added CircuitPython compatibility for missing `os.path.join` and `os.path.isfile`. |
| `f3536acb6f571eb1bf5498cad02f9d9213eb06eb` | Aligned the verifier with all 20 hashed payloads. |
| `63ede243319e793b095f537957d991be5d0a3d1d` | Added `hashlib.sha256`/`hexdigest` compatibility through `hashlib.new("sha256")`. |
| `67ab1edf2cae12985d344ec37f5ad97a1b2071d0` | Added the filesystem persistence/maintenance contract. |
| `dd006a370bf6b43c17ed5f17709ca7815fd76ab5` | Added calibration audio cues and six distinct profile notes. |
| `9d32e09bd6e53fc506f847bff3fc28ad1fa64a8c` | Accepted the compact `OK|LUX|lux=…|sensor=ok` response in Classroom Studio. |
| `a84849447fe6773dd1a006ec0e8582c1161c56c5` | Executed live `SETRES` and `BEEP` locally on the Pico; GP6 passive-piezo output added. |
| `88ff59fcbb8d6c0613e2f76ee77c9f9da766f893` | Added a Combined Guard route adapter for Buzzer actions (`BEEP`/`DELAY`). |
| `79b4618700bd5a275d6241363d1e00ba43573184` | Bypassed the second legacy strict-plan compile path that still rejected Buzzer during export. |

## Failure sequence and conclusions

### Boot and CircuitPython compatibility

Hardware bring-up exposed, in order: low-memory import failures, a false JSON read diagnosis, missing `os.path`, an 18-vs-20 manifest allowlist mismatch, and missing `hashlib.sha256()`. The fixes above produced a clean Boot and a working read-only control plane without creating or copying `ams_key.json`.

### Light telemetry

The sensor hardware was healthy. The application parser incorrectly required an older response shape. After commit `9d32e09…`, Classroom Studio correctly accepts responses such as:

```text
OK|LUX|lux=10.8|sensor=ok
```

### Live Buzzer

The initial calibration-audio change did not implement the ordinary Classroom Studio Buzzer Step. The first live run therefore timed out on `SETRES`. Commit `a8484944…` added local handling for both `SETRES` and `BEEP`.

### Combined Guard exporter

The first exporter adapter fixed route compilation, but export still failed because `PicoFirmwareExporter.Export()` passed all real steps into the legacy strict `PlanExporter`, which rejected `buzzer`. Commit `79b46187…` uses the legacy exporter only for compatible staging with an empty step list while actual routes continue through the Combined Guard adapter.

## Bundle validation history

All accepted bundles contained exactly 21 files, 20 manifest entries, zero unsafe paths, and zero internal hash mismatches unless otherwise noted.

| Bundle | ZIP SHA-256 | Outcome |
|---|---|---|
| `stage2` | `d2e4a71619467e03c961006a565abfc674b86769b6cf52aa6dfc52e97a224bed` | First corrected 21-file baseline. |
| `stage6` | `a02f749544e0cb8d413ef917d71e74d6b7fdc6b09143320512195b7ea8b45cb5` | Exposed missing CircuitPython `os.path`. |
| `stage7` | `52e2b1f3e69d6aafcc5e92c2adc470d88acb8347d34d7c151325548ee1e6ac01` | Exposed verifier inventory mismatch. |
| `stage8` | `c9abcc78b140c8be4c871aca233ab56ec75046ba866b5811cead9e8e033e5fd3` | Internally valid but stale; lacked inventory fix. |
| `stage9` | `648b1b7b61829b7bbadbb3bc862c7ff7c1453cb3cfdfa83b7095efebc04e3cf6` | Exposed missing `hashlib.sha256`. |
| `stage10` | `c1d7a4ebb1015f96225ac055aa24b9b530756b666f8e4bc3fb898ac464fc0d87` | Boot and direct control plane passed. |
| `stage11` | `1293441adaf1122e6587b4ee8bc3c3c1f1376615a0097dc84ca630f52d2e039e` | Auto-port, persistence, calibration audio, and compact-light-parser baseline. |
| `stage12` | `6ad814f2311d9ee25c3d9554cf3d85410e8d696b11fee9b8a35c279265613c25` | Installed; live `SETRES` and Buzzer Step passed. |

## Stage12 validation and hardware evidence

Archive validation:

- 21 files; 20 manifest entries.
- Zero hash mismatches and zero unsafe ZIP paths.
- All Python files passed syntax compilation.
- Boot GP3 maintenance contract present.
- `role=brain`, live `SETRES`, live `BEEP`, GP6 output, and six calibration notes present.
- No Combined Guard exporter sentinel leaked into route files.
- This particular archive was exported before the Buzzer Step was added, so its route files contain no Buzzer operation. This does not affect the live-step test or firmware functionality; route serialization remains a separate later gate.

Hot-plug and connection evidence:

```text
hot-plug: board detected on COM30, COM31 — connecting automatically
port_open: COM31
connected: ...|profiles=6|role=brain
OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6|role=brain
```

Live execution evidence from `ams-log-20260917-204755.txt`:

```text
→ SETRES|1920,1080
← OK|SETRES
→ BEEP|2637,66
← OK|BEEP
...
run finished
```

Every emitted BEEP received `OK|BEEP`, the run completed without timeout, and the user confirmed audible output from the physical buzzer. This closes the live Buzzer Step gate.

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute an operational route, macro, HID action, or actuator.
- Do not create or copy `ams_key.json`.
- Do not write unrelated files to the Pico during calibration.
- Keep PR #175 Draft; do not merge or release.
- Route serialization and first non-empty route memory behavior remain separate unapproved gates.

## Exact next action: calibration-entry audio only

1. Keep Classroom Studio connected on COM31 and ensure no Buzzer run is in progress.
2. Hold the blue GP4 button for about five seconds, then release after the calibration-entry cue.
3. Require a distinct audible cue and, where visible, `EVT|CAL|mode=ready|stage=1|id=desktop|seconds=5|saved=0`.
4. Do not press GP4 again; it may exit calibration.
5. Do not press yellow GP3 yet.
6. Stop and report whether the entry cue was audible.

After this passes, calibrate only the `desktop` profile: short-press yellow GP3 to start a five-second sample, wait for `mode=complete-stage`, then short-press GP3 again to save. Require:

```text
EVT|CAL|mode=saved-stage|stage=1|id=desktop|saved=1
```

Review center, spread, and tolerance before advancing to the next profile.
