# Phase 7 exporter fix — 2026-09-17

## Source change

- Repository: `c4haztex/smc-1`
- Branch: `phase7/light-guard-calibration`
- Draft PR: #175
- New source head: `0767c6fffdc89741db8a99b36494aa6ad6049949`
- Commit message: `fix: harden Combined Guard export documentation gate`

## Fixed defect

The Combined Guard exporter reused legacy `PicoFirmwareExporter` output for `README-FLASH.md` and `pico-calibration.json`. The generated package therefore contained stale v0.9.64f, CircuitPython 9.x, three-file, and `adafruit_hid` instructions that contradicted the actual 21-file low-memory runtime.

The fix now replaces both files before generating `SHA256SUMS.txt`:

- README reports Classroom Studio v0.9.67.
- README lists the exact complete 21-file bundle.
- Validated target is CircuitPython 10.3.0.
- README explicitly says not to install or copy `adafruit_hid`.
- Metadata identifies `combined-pico-guard-executor`, includes the calibration revision, and records `hardwareCalibrationVerified: false`.
- Export fails if its resulting inventory is not exactly the expected 21 files.

A new portable regression test checks the current metadata, exact inventory, no legacy 9.x/`adafruit_hid` instruction, and the fail-closed calibration gate.

## CI result

For head `0767c6fffdc89741db8a99b36494aa6ad6049949`:

- 12 executable checks succeeded.
- `autocycle / downloadable test package` was skipped by the existing branch condition.
- Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35204909737
- Artifact name: `light-state-windows-output`

## Remaining gate

Do not copy files to `CIRCUITPY` yet. Download the fresh artifact, verify provenance against the new head, export a new 21-file staging bundle, and revalidate all hashes and generated documentation. Hardware preflight remains blocked until those checks pass.
