# Test and release matrix

## Required on every phase

- Existing Windows build/TestRunner: zero failures.
- Portable/PLAN2 compile, golden, parser and simulation gates: green.
- Sensitive-content guard: green.
- Old settings and old `.amsj` compatibility fixture.
- No version bump until the feature PR is merged and accepted.

## Phase-specific gates

| Phase | Pure/unit gate | Integration gate | Hardware gate |
|---:|---|---|---|
| 1 | pin allowlist/conflict/default migration | base + AutoCycle export parity | selected alternate pin drives passive buzzer |
| 2 | deterministic rolling statistics/ring bounds | start/stop/disconnect/no-sensor | simultaneous lux/sound observation without Run interference |
| 3 | range/time-window evaluator | guard blocks before first HID | wrong profile, RTC missing, out-of-hours, valid profile |
| 4 | result/report model | repeatable wizard with optional devices | complete board bench pass |
| 5 | CFG/data-flow fixtures | Run and Export share diagnostics | panic release remains effective |
| 6 | deterministic seeded trace | assert zero real adapters called | no movement/typing on connected hardware |
| 7 | request state machine/race tests | pause/timeout/nested-step interactions | skip/retry/stop-after-current bench pass |
| 8 | bounded retry/recovery graph | host/portable parity or blockers | fatal and recoverable failures |
| 9 | parser/type/scope/resource limits | host/Pico differential suite | restart/reset/persistence behavior |

## Merge checklist

1. Scope is limited to one phase.
2. New settings have absent-field defaults.
3. Generated artifacts state their schema/protocol version.
4. Negative tests prove failure is visible and safe.
5. README/wiring output matches actual firmware.
6. CI is fully green.
7. Hardware-required phases have an attached observation/log before release.
8. Release notes identify the exact accepted baseline and rollback path.

## Conflict watch after PR #63

Immediately re-audit these before phases 5–8: `StepDefinitions.cs`, `StepDialog`, all insertion surfaces, `RunEngine`, error policy services, plan exporter/runtime parser and `TestRunner` step-count/meta guards. Do not copy stale code from this preparation baseline.