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
- reduces the runtime from 20,897 to 20,200 bytes;
- adds tests for key mapping, modifiers, six-key rollover, and missing HID devices.

## Next gate

1. Download `light-state-windows-output` from run `35193972785`.
2. Verify artifact provenance against code head `27f72856e17b1772c1611a14aef6a5c363432f26`.
3. Calculate and record SHA-256.
4. Inspect the packaged runtime and confirm that `Keycode` and `adafruit_hid` are absent.
5. Run a fresh export.
6. Build the final ZIP and record its SHA-256.
7. Only then begin controlled preflight installation on the new Pico.

## Active safety constraints

Until the artifact gate is complete:

- do not write anything to `D:\`;
- do not reinstall packages built from the old head `f8207578…`;
- do not send `GUARD|ON`;
- do not press GP4 or GP3;
- do not flash/reset or change Serial/USB connections;
- do not run any actuator;
- do not merge or release PR #175.

## Input provenance note

The large ZIP supplied with the continuation request is a Notion project export/archive. It is **not** the fresh GitHub Actions artifact and does not open the installation gate.

## Documentation isolation

This handoff lives on a dedicated documentation branch so the validated code head and artifact provenance of PR #175 are not changed by a docs-only commit.
