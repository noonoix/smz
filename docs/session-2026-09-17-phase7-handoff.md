# Phase 7 handoff — 2026-09-17

## Purpose

Durable continuation checkpoint for the Light Guard Phase 7 hardware-acceptance session. This document records only technical state, evidence, safety gates, and the next action; the full chat transcript remains outside the repository.

## Repository state at checkpoint

- Repository: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Draft PR: #175
- Validated code head: `27f72856e17b1772c1611a14aef6a5c363432f26`
- PR state: open, draft, mergeable state clean
- CI: 12 successful checks; `autocycle / downloadable test package` skipped as expected
- Windows artifact run: https://github.com/c4haztex/smc-1/actions/runs/35193972785
- Required artifact: `light-state-windows-output`

## Confirmed failure and fix

A controlled console diagnostic on CircuitPython 10.3.0 showed startup failure before the runtime loop:

```text
File "code.py", line 3, in <module>
File "combined_guard_runtime.py", line 129, in <module>
MemoryError: memory allocation failed, allocating 2947 bytes
```

No route, macro, HID action, or actuator ran. Fail-closed behavior was preserved.

The low-memory patch in the validated head:

- removes `class Keycode`;
- uses direct, allocation-free VK-to-HID usage conversion;
- keeps the internal `Keyboard` driver;
- keeps `release_all()` on Stop/HALT;
- reduces the LF-normalized runtime from 20,897 to 20,200 bytes;
- adds tests for key mapping, modifiers, six-key rollover, and missing HID devices.

## Received artifact validation

Received file: `light-state-windows-output(5).zip`

- ZIP size: 3,595,513 bytes
- ZIP SHA-256: `946467af0ccf3096e3d51de4aa331e4a23b9e7f02eeaeeb6a1d63291418b252e`
- ZIP integrity: pass; 83 entries; no unsafe traversal paths
- Embedded source marker: `27f72856e17b1772c1611a14aef6a5c363432f26`
- Artifact runtime Git blob after CRLF→LF normalization: `fe2e6100e8113ad69d31d845f98f1ca68a9f55b9`
- Repository runtime blob at the validated commit: `fe2e6100e8113ad69d31d845f98f1ca68a9f55b9`
- `combined-runtime` and `portable-runtime` copies: byte-identical
- Raw CRLF runtime size: 20,584 bytes; LF-normalized size: 20,200 bytes
- Runtime SHA-256 (raw artifact copy): `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`
- Actual runtime contains no `class Keycode` and no `adafruit_hid` import
- Internal `Keyboard` and `release_all()` are present
- Python syntax check: pass
- Windows tests: 769 passed, 0 failed
- Light telemetry/authorization suites: all reported groups passed with 0 failed

The `adafruit_hid`/`Keycode` strings found in `portable-runtime/autocycle_h6_patch.json` are historical patch search text, not imports in either packaged `combined_guard_runtime.py` copy.

The Windows log contains a CI-safe skipped decoder fixture because `daroon1.amk` and its local decoder path were absent. The final suite still reports 769 passed and 0 failed. Companion publish completed with UI Automation reference-resolution warnings but produced the companion output successfully.

## Next gate

Artifact provenance and static runtime validation are complete. The next operation is software-only execution and export to a new empty staging directory on Windows:

1. Extract the received ZIP to a normal local folder, not `D:\` and not directly inside the ZIP.
2. Launch `ClassroomStudio.exe` normally, not as administrator.
3. Keep Pico/Arduino operations prohibited.
4. Use the software-only Companion to list/attach, read status, and export the Combined Guard bundle to an empty staging directory.
5. Verify the exported bundle manifest and SHA-256 manifest.
6. Package the verified staging output and record its SHA-256.
7. Only after those results are reviewed may controlled Pico preflight begin.

## Active safety constraints

Until the exported bundle gate is complete:

- do not write anything to `D:\`;
- do not reinstall packages built from the old head `f8207578…`;
- do not send `GUARD|ON`;
- do not press GP4 or GP3;
- do not flash/reset or change Serial/USB connections;
- do not run any actuator;
- do not merge or release PR #175.

## Documentation isolation

This handoff lives on a dedicated documentation branch so the validated code head and artifact provenance of PR #175 are not changed by a docs-only commit.
