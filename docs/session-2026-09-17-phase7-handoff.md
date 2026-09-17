# Phase 7 handoff — 2026-09-17

## Purpose and synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records the complete technical checkpoint: decisions, evidence, hashes, safety gates, failures, fixes, current state, and next action. The full chat transcript is intentionally not copied.

From this checkpoint forward, every substantive update to the Notion session must be mirrored into this file in the same work step. This file remains on the dedicated `docs/session-2026-09-17-handoff` branch so documentation-only commits do not alter artifact provenance on the code branch.

## Current state

- Repository: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Draft PR: https://github.com/c4haztex/smc-1/pull/175
- Current validated head: `63ede243319e793b095f537957d991be5d0a3d1d`
- PR state: open, Draft, mergeable state clean
- Current CI: 12 executable checks succeeded; `autocycle / downloadable test package` skipped by branch condition
- Current Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35236330789
- Installed hardware bundle: `stage10`
- Hardware gate: Boot and read-only control plane passed
- Active phase: controlled six-profile physical calibration; no profile has been captured yet

## Architecture and fixed wiring contract

- Classroom Studio owns authoring, export, calibration synchronization, and manual desktop testing.
- A regular Raspberry Pi Pico runs the validated bundle independently after deployment.
- Arduino arm remains responsible for mouse/sound; it is not removed.
- BH1750/GY-30: 3V3, GND, SDA=GP20, SCL=GP21, address `0x23`.
- GP4 blue button: Start/Stop; hold for three seconds to enter/exit calibration.
- GP3 yellow button: Pause/Resume outside calibration; sample/save inside calibration.
- GP6: passive piezo.
- UART0 to arm: GP16 TX, GP17 RX, 57600 8N1 with common ground.
- COM17 / MI_00: CircuitPython console.
- COM28 / MI_02: USB CDC data/control plane.

## Canonical calibration profiles

1. `desktop`
2. `login-or-dc`
3. `character-dashboard`
4. `entering-game-loading`
5. `game`
6. `targeted`

Each physical sample lasts five seconds. The runtime uses median center, rejects fewer than five readings or spread greater than 5 lux, computes tolerance as `max(2.0, spread * 1.5)`, and uses `stable_ms=750`.

## Durable code fixes made during hardware bring-up

| Commit | Change |
|---|---|
| `0767c6fffdc89741db8a99b36494aa6ad6049949` | Corrected exporter README/metadata and enforced the complete 21-file bundle inventory. |
| `df94be8ecaf986feb7160dabb2930dde06ab185f` | Corrected Bridge identity handling while preserving fail-closed behavior. |
| `fd63358bcbbf54a761c1df3e1cdafcff5d85ea3d` | Changed early import order after the first hardware MemoryError. |
| `8ddf5d7a006688d729eb129b2bb1a324f30f9f75` | Deferred the 57 KB plan engine until actual route execution. |
| `a8cf753bd93fa7055b493f3fced7dfcb0478eb73` | Preserved the workflow entrypoint contract after bundle-first loading. |
| `3abf5f9898864e4c6290872106ce6d00aa7afe12` | Parsed the bundle on a fresh heap before importing the combined runtime and reused the parsed result. |
| `bad1e2a70dec761aa32b19bc6d428134dd4e8acf` | Added CircuitPython compatibility for missing `os.path.join` and `os.path.isfile`. |
| `f3536acb6f571eb1bf5498cad02f9d9213eb06eb` | Aligned the verifier with the exporter’s 20 hashed payloads, including `pico-calibration.json` and `README-FLASH.md`. |
| `63ede243319e793b095f537957d991be5d0a3d1d` | Added `hashlib.sha256`/`hexdigest` compatibility using CircuitPython `hashlib.new("sha256")`. |

## Failure sequence and conclusions

### Initial memory failures

The original eager import failed before the runtime loop:

```text
MemoryError: memory allocation failed, allocating 2947 bytes
```

Later import arrangements also exposed an allocation failure around 3112 bytes while importing `plan_engine.py`. No route, HID action, macro, or actuator ran. The engine is now deferred.

### JSON investigation

Repeated generic errors claimed `guard-transition.json` could not be read. Direct REPL diagnostics proved the file and JSON parser were valid:

```text
MEM0 154656
READ 1617 MEM1 152272
JSON combined-pico-guard-executor MEM2 149008
MEM_AFTER 148784
MEM_CLEAN 151184
```

This led to bundle pre-parse on a fresh heap and reuse of the parsed bundle.

### CircuitPython `os.path`

The next traceback exposed the hidden underlying exception:

```text
AttributeError: 'module' object has no attribute 'path'
```

A minimal proxy now supplies only `join` and `isfile` while delegating other operations to CircuitPython `os`.

### Manifest inventory mismatch

The exporter correctly hashes 20 payloads in a 21-file bundle, but the board allowlist originally expected 18. This caused:

```text
GuardBundleError: unexpected or duplicate SHA256SUMS file: pico-calibration.json
```

`pico-calibration.json` was neither unexpected nor duplicated. The verifier now admits and verifies both `pico-calibration.json` and `README-FLASH.md`.

### CircuitPython SHA-256 API

After inventory verification began, CircuitPython exposed `hashlib.new("sha256")` but not `hashlib.sha256()`:

```text
AttributeError: 'module' object has no attribute 'sha256'
```

The bootstrap now supplies compatible `sha256()`, `update()`, `digest()`, and `hexdigest()` behavior. The wrapper passed the standard SHA-256 vector for `abc`:

```text
ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
```

## Bundle validation history

| Bundle | ZIP SHA-256 | Outcome |
|---|---|---|
| `stage2` | `d2e4a71619467e03c961006a565abfc674b86769b6cf52aa6dfc52e97a224bed` | Complete 21-file corrected exporter bundle; initial hardware baseline. |
| `stage3` | `70149cc29e7a638c8bdb9c23fdc12a81965a0c1eadb20870a36c44b7cba26ddc` | Valid bundle; exposed import-order memory pressure. |
| `stage4` | `7be65cd13e435ba0cc52b0fd2ef4f79354a5f24a8442169d29660761e87bacac` | Valid bundle; further isolated JSON/loading order. |
| `stage5` | `6ec6318da762f3fdcbaddd53a733812d844338cac412da469c5cc0054215f81c` | Valid bundle; board manifest required recopy before matching. |
| `stage6` | `a02f749544e0cb8d413ef917d71e74d6b7fdc6b09143320512195b7ea8b45cb5` | Valid bundle; exposed missing CircuitPython `os.path`. |
| `stage7` | `52e2b1f3e69d6aafcc5e92c2adc470d88acb8347d34d7c151325548ee1e6ac01` | Valid bundle; exposed 18-vs-20 verifier inventory mismatch. |
| `stage8` | `c9abcc78b140c8be4c871aca233ab56ec75046ba866b5811cead9e8e033e5fd3` | Internally valid but stale; did not contain the inventory fix. |
| `stage9` | `648b1b7b61829b7bbadbb3bc862c7ff7c1453cb3cfdfa83b7095efebc04e3cf6` | Valid and copied correctly; exposed missing `hashlib.sha256`. |
| `stage10` | `c1d7a4ebb1015f96225ac055aa24b9b530756b666f8e4bc3fb898ac464fc0d87` | Valid, installed, Boot passed, control plane passed. |

Every accepted stage ZIP had exactly 21 files, 20 manifest entries, no unsafe paths, and zero internal hash mismatches unless explicitly noted as a board-side recopy issue.

## Stage10 evidence

Archive validation:

- ZIP SHA-256: `c1d7a4ebb1015f96225ac055aa24b9b530756b666f8e4bc3fb898ac464fc0d87`
- 21 files; 20 manifest entries; zero hash errors; no unsafe path
- All Python files compile under host syntax checking
- Inventory, `os.path`, SHA-256/hexdigest, pre-parse, and deferred-engine markers present

Installed board hashes exactly match stage10:

```text
code.py         0D949CD78908625A5D1DB709CDB8C1B5CAEE01DF192F90B101DC3290C35EBAD1
SHA256SUMS.txt  0F1230E5DD7F978B6AB566C6173EFE319F9BDDC45380DFCE90B701829660ED0D
```

Stable runtime:

```text
combined_guard_runtime.py
2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5
```

A soft reboot produced no traceback and entered the runtime loop. Classroom Studio identified the board and showed a green connection. Independent read-only control-plane checks on COM28 returned:

```text
PING => OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6
LUX? => OK|LUX|lux=73.3|sensor=ok
CALGET => OK|CALGET|revision=guard-bf2929070db779e4|count=6
```

This closes the Boot and read-only control-plane gates. It does not yet approve Guard ON or route execution.

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute a route, macro, operational HID action, or actuator.
- Do not create or copy `ams_key.json`; it belongs to a different direct encrypted arm path.
- Use GP4/GP3 only within the explicit calibration sequence. A short GP4 press outside calibration is prohibited.
- Do not write unrelated files to the Pico during calibration.
- Keep PR #175 Draft; do not merge or release.

## Exact next action: desktop calibration only

1. Keep Classroom Studio connected and green on COM28; ensure no other serial client owns the port.
2. Display the real Desktop state and keep room light, monitor, board, and sensor stable.
3. Hold GP4 for about three seconds, then release. Do not tap it. Require:

   ```text
   EVT|CAL|mode=ready|stage=1|id=desktop|seconds=5|saved=0
   ```

4. Short-press GP3 once to start the sample. Require:

   ```text
   EVT|CAL|mode=started|stage=1|id=desktop|seconds=5|saved=0
   ```

5. Do not move or change the screen for at least five seconds. Require `mode=complete-stage`. If `ERR|CAL|UNSTABLE` appears, stabilize conditions and short-press GP3 once to retry.
6. Only after `mode=complete-stage`, short-press GP3 again to save. Require:

   ```text
   EVT|CAL|mode=saved-stage|stage=1|id=desktop|saved=1
   ```

7. Stop before pressing GP4 for the next profile. Review `center`, `spread`, and `tolerance` first.

## Later gates

After all six profiles are captured and saved, the local revision will be `pending`. Synchronize the calibration through Classroom Studio, verify the final revision with `CALGET`, then separately test first-route memory behavior. Because `plan_engine.py` is deferred, a non-empty route may still expose an OOM and must be tested as a distinct gate. Production acceptance, merge, and release remain out of scope until those checks pass.
