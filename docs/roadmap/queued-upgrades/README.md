# Queued upgrades — implementation preparation

This package prepares the selected Classroom Studio upgrades without modifying app, firmware, runtime, version pins or release workflows.

## Concurrency boundary

Active work is PR #63 (`feature/error-step-timeout-ui`). It changes per-step timeout behavior, the mandatory `raiseError` step, insertion surfaces, runtime error routing and `TestRunner` counts.

Until PR #63 is merged and green, this preparation branch must remain documentation-only. In particular, do not edit `StepDefinitions.cs`, `RunEngine.cs`, `MainWindow*`, `OptionsDialog*`, Pico templates or `tests/TestRunner.cs` here.

## Ordered execution

| Order | Issue | Feature | Earliest start |
|---:|---:|---|---|
| 1 | #66 | Configurable buzzer GPIO | After PR #63 is merged |
| 2 | #74 | Live sensor monitor + statistical calibration | After phase 1 is accepted |
| 3 | #75 | Portable profile + pre-Launch guard | After phase 2 establishes trusted light measurements |
| 4 | #67 | Hardware self-test wizard | After pin/profile contracts are stable |
| 5 | #65 | Control-flow-aware Key Down/Key Up validation | After PR #63 error exits are final |
| 6 | #70 | Side-effect-free Dry Run | After validator/control-flow model is reusable |
| 7 | #71 | Live run controls | After Dry Run and safe-boundary semantics settle |
| 8 | #73 | General per-step error behavior | Re-scope after PR #63; do not duplicate timeout/raiseError work |
| 9 | #72 | Variables and advanced conditions | Last; requires stable flow/error contracts |

Parent tracking issue: #64.

## One-feature release rule

Each phase gets its own branch, PR and acceptance gate. A phase may not share a version bump or release PR with the next phase. If a hardware gate fails, fix it on the same phase branch before opening the next phase.

## Baseline refresh checklist

Before starting every phase:

1. Confirm the latest green release and `main` SHA.
2. Rebase the phase branch from that exact `main`.
3. Re-read changed files from the prior phase.
4. Run existing Windows, portable, PLAN2 and sensitive-content gates before editing.
5. Record new protocol/version changes explicitly; never silently reinterpret old `.amsj` or settings files.
