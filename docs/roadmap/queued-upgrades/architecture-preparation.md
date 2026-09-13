# Architecture preparation

## Shared invariants

- Classroom Studio is the build/configuration environment; standalone execution remains on Pico.
- No permanent Windows helper, service, startup entry or continuous host process is introduced by these phases.
- Old settings and `.amsj` files must remain readable.
- Every new portable behavior either has host/Pico parity or an explicit export blocker.
- All buffers, histories, retries, charts, variables and traces are bounded.
- Stop/panic paths always release held keyboard and mouse state.

## Phase 1 — configurable buzzer pin

**Prepared data model**

- `AppSettings.BuzzerGpio`: string, default `GP6` when absent.
- Central pin registry with owner, direction, capability and reserved reason.
- Export-time allowlist rather than accepting arbitrary `board.*` text.

**Known reservations**

- `GP3/GP4`: physical controls.
- `GP16/GP17`: UART arm.
- `GP20/GP21`: BH1750 I2C.

**Touch map**

`AppSettings`, behavior/options UI, `PicoFirmwareExporter`, `AutoCycleFirmwareBundle` manifest/adapter, generated README/wiring text and exporter tests.

## Phase 2 — live sensors and calibration statistics

**Prepared service split**

- Pure `RollingSensorStats`: count, min, max, mean and spread with a fixed-capacity chart ring.
- `SensorMonitorSession`: cancellation, cadence, connection state and idle/run interlock.
- UI consumes immutable snapshots; serial callbacks never mutate WPF controls directly.

**Protocol decision to make on the phase branch**

Prefer bounded one-shot reads or an explicitly stoppable stream. Monitoring is allowed only while no plan is running. Preserve `LCAL|ms` and `SCAL|ms` compatibility.

**First-release rule**

Display measurements only. Do not automatically change `luxCenter`, `luxTolerance` or sound threshold. The user owns the final values.

## Phase 3 — profile guard

**Prepared portable artifact**

A versioned, bounded `profile_guard.json` (or equivalent compiled section) containing profile id, lux ranges, stable duration, allowed time windows, alarm behavior and schema version. It must contain no machine secret or continuous activity history.

**Fail-closed sequence**

1. Before Launch/Auto Resume, release any stale HID state.
2. Validate sensor availability and stable profile lux.
3. Validate trusted wall time.
4. On mismatch/ambiguity/missing trusted time: stay stopped and alarm.
5. Only then permit the first HID operation.

**Blocking architecture decision**

A standard Pico has no trustworthy wall clock across power loss. Select hardware RTC and its pins, battery behavior and drift policy before implementation. Without trusted time, the time gate is unavailable rather than guessed.

## Phase 4 — hardware self-test

Prepare independent test adapters for identity/version, UART, BH1750, sound, buzzer, controls, keyboard and mouse. Results are `Pass`, `Fail` or `Skipped` with reason. The report is bounded and user-exported only.

## Phase 5 — key-state validator

Build a reusable control-flow graph over pipeline tabs, branches, loops, labels/gotos, packages, parallel groups, timeout/error exits and includes. Data-flow state is the set of possibly-held keys. Merge is union; a safe terminal state has an empty set. Report both unmatched `Key Up` and any terminal path with held keys.

## Phase 6 — Dry Run

Reuse the graph and execution interfaces with fake adapters for board, HID, process, file and audio operations. Randomness receives a visible seed. External waits receive scripted outcomes. Dry Run must make zero transport or OS side effects.

## Phase 7 — live controls

Introduce requests, not immediate mutations: `SkipCurrent`, `RetryCurrent`, `StopAfterCurrent`. `RunEngine` consumes them only at documented safe boundaries. Retry requires an idempotency classification; unsafe operations are not retried silently.

## Phase 8 — general per-step error behavior

After PR #63, inventory what already exists. Keep mandatory `raiseError` as immediate stop + alarm. Add policies only to eligible steps and cap retry/recovery recursion. Define portable opcode/schema changes before UI work.

## Phase 9 — variables and conditions

Prepare typed values (`number`, `text`, `bool`), explicit scopes, bounded counts/string sizes/expression depth and reset rules for Start, Stop, Restart, Auto Resume and Include. Any PLAN format change requires versioned parser/exporter compatibility and differential host/Pico tests.
