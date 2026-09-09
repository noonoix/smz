# Portable Plan v2 — full Classroom Studio step support

## Decision
Develop in phases, not as one combined hardware + exporter jump. First validate the v0.9.65/arm-2.3 transport baseline on hardware; then land Plan v2 on a separate branch. This prevents UART faults from being confused with plan-engine/exporter faults.

## Phase 1 — deterministic portable core
- `PLAN|2`; SCREEN calls SETRES once per run.
- MOVETO/RMOUSE, CLICK, TYPE, DELAY.
- KEY/KDOWN/KUP/WHEEL.
- LOOP/LOOPTIME with Play Options baked into plan (`once`, `times`, `timed`; timed passes finish after crossing deadline, matching the app).
- WSND/TRGSND, WLIGHT/TRGLUX.
- IFSND/IFLUX + ELSE/ENDIF.
- LABEL/GOTO with block-chain visibility and loop unwinding.
- INCLUDE with depth cap 4 and cycle guard.
- RAW escape hatch.
- `.amsj + ams-settings.json -> plan.txt` reference generator and checker.

## Phase 2 — C# integration
- `Services/PlanExporter.cs` as a pure builder plus export service.
- File menu command: Export Pico Plan.
- Bundle code65, plan_engine v2 and generated plan.txt in application output.
- Golden fixtures for clap -> human mouse 10 s and one-minute timed repeat.
- App TestRunner coverage and CI checks; version bump on the feature branch.

## Phase 3 — complex and PC-dependent steps
- `randomPackage`: deterministic portable representation with fresh choice each pass.
- `parallelGroup`: define portable cooperative scheduling; do not fake true parallelism.
- `playScript`: recursive INCLUDE conversion, depth/cycle protection.
- `findImage`, `playAudio`, `runExe`, `openFile`: explicitly classify as PC-required or add a board-side asset/runtime contract. Never silently skip them in a “full support” export.

## Definition of complete support
Every Classroom Studio step type must be one of:
1. faithfully executable on Pico/arm;
2. explicitly marked PC-required with a blocking export diagnostic; or
3. supported through a documented portable asset/runtime contract.
No silent skips. Disabled steps remain skipped by design; structural markers are consumed by the exporter.
