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

## Confirmed memory failure and fix

A controlled console diagnostic on CircuitPython 10.3.0 showed startup failure before the runtime loop:

```text
File "code.py", line 3, in <module>
File "combined_guard_runtime.py", line 129, in <module>
MemoryError: memory allocation failed, allocating 2947 bytes
```

No route, macro, HID action, or actuator ran. Fail-closed behavior was preserved.

The low-memory patch in the validated head removes `class Keycode`, uses direct VK-to-HID conversion, keeps the internal `Keyboard` driver and `release_all()`, and reduces the LF-normalized runtime from 20,897 to 20,200 bytes.

## Windows artifact validation

Received file: `light-state-windows-output(5).zip`

- ZIP SHA-256: `946467af0ccf3096e3d51de4aa331e4a23b9e7f02eeaeeb6a1d63291418b252e`
- ZIP integrity: pass; 83 entries; no unsafe traversal paths
- Embedded source marker: `27f72856e17b1772c1611a14aef6a5c363432f26`
- Artifact runtime Git blob after CRLF→LF normalization matches the repository blob: `fe2e6100e8113ad69d31d845f98f1ca68a9f55b9`
- `combined-runtime` and `portable-runtime` copies are byte-identical
- Runtime contains no `class Keycode` and no `adafruit_hid` import
- Windows tests: 769 passed, 0 failed
- Light telemetry/authorization suites: all groups passed with 0 failed

## Local staging export validation

The operator launched Classroom Studio v0.9.67 from the extracted artifact with the board disconnected and exported a Combined Guard bundle to `C:\stage`.

Received archive: `stage.zip`

- ZIP size: 34,514 bytes
- ZIP SHA-256: `291b65511c08315b9b110131be1aed9f2f76ad94ae708cfca46453f4c8b614a9`
- Structure: 21 files, no directories, no unsafe paths
- `SHA256SUMS.txt`: 20 entries; all 20 match actual file bytes
- CRLF manifest lines are accepted by the runtime parser, which applies `raw.strip().split()`
- Guard transition/calibration JSON is valid; shared revision: `guard-bf2929070db779e4`
- Runtime: 20,584 raw CRLF bytes / 20,200 LF-normalized bytes
- Runtime SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`
- No `class Keycode`; no `adafruit_hid` import; internal `Keyboard` and `release_all()` present
- All route files contain only `PLAN|2`, matching the intentionally empty workspace

## Installation blocker

`README-FLASH.md` generated into the hashed bundle is stale and contradicts the actual package:

- generator is labeled `Classroom Studio v0.9.64f`, not v0.9.67;
- documentation lists only three files, while the bundle contains 21;
- it instructs installation of CircuitPython 9.x;
- it instructs copying `adafruit_hid`, although the current runtime intentionally has no such dependency.

`pico-calibration.json` also has `states: []`, and the UI reports hardware calibration is not verified.

## Gate decision

Static integrity and provenance gates passed, but the hardware installation gate remains closed because the package contains unsafe/stale operator instructions and unverified calibration metadata.

Next actions:

1. Correct exporter-generated `README-FLASH.md` and generator metadata.
2. Regenerate the Windows artifact from a new reviewed head.
3. Re-export to an empty staging directory on Windows.
4. Revalidate provenance, inventory, JSON, and all hashes.
5. Only then consider controlled Pico preflight.

Until then: do not write to `CIRCUITPY`, do not send `GUARD|ON`, do not press GP4/GP3, do not flash/reset, and do not merge or release PR #175.

## Documentation isolation

This handoff lives on a dedicated documentation branch so the validated code head and artifact provenance of PR #175 are not changed by docs-only commits.
