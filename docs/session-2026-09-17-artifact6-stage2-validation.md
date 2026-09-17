# Phase 7 fresh artifact and stage2 validation — 2026-09-17

## Source

- Repository: `c4haztex/smc-1`
- Branch: `phase7/light-guard-calibration`
- Draft PR: #175
- Source head: `0767c6fffdc89741db8a99b36494aa6ad6049949`
- Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35204909737

## Windows artifact

- File: `light-state-windows-output(6).zip`
- SHA-256: `bb1ff0a18afac8f21eec73942e6f228425b682f396a16baca0595b8868c87e18`
- Provenance marker matches the source head.
- Build version: `ClassroomStudio/0.9.67`
- ZIP integrity: pass; 83 entries; 9,298,564 expanded bytes; no unsafe paths.
- Windows TestRunner: 771 passed, 0 failed.
- Light telemetry and authorization suites: all groups passed with 0 failed.

## Fresh staging export

- File: `stage2.zip`
- SHA-256: `d2e4a71619467e03c961006a565abfc674b86769b6cf52aa6dfc52e97a224bed`
- Inventory: exactly 21 files; no directories or unsafe paths.
- `SHA256SUMS.txt`: all 20 payload hashes match.
- README identifies Classroom Studio v0.9.67, the exact 21-file package, CircuitPython 10.3.0, and the no-`adafruit_hid` contract.
- `pico-calibration.json` identifies `combined-pico-guard-executor`, revision `guard-bf2929070db779e4`, and `hardwareCalibrationVerified: false`.
- Runtime SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`.
- Runtime is byte-identical to the Windows artifact copy, 20,200 LF-normalized bytes, with no `class Keycode` or `adafruit_hid` import.

## Gate decision

Fresh artifact provenance and staging-export integrity passed. The next allowed operation is read-only Pico preflight: inspect the target board identity, `boot_out.txt`, CircuitPython version, and current root inventory. Do not copy the bundle to `CIRCUITPY` until that evidence is reviewed. Keep Guard OFF; do not press GP4 or GP3; do not merge or release PR #175.
