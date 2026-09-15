# Phase 5 — Fail-closed Light-State Execution Gate

Tracking: #163

## 1. Purpose

Define a deterministic, auditable gate between the read-only light-state classifier and any future actuator. This phase is **contract and test design only**. It must not execute macros, HID input, BEEP, `WLUX`, `TRGLUX`, Launch, Auto Resume, or any Pico/Pro Micro command.

## 2. Non-negotiable boundary

```text
Lux telemetry -> classifier -> gate evaluator -> diagnostic decision
                                             X no actuator connection
```

The evaluator is a pure decision component. `Eligible` means only “the supplied observation satisfies the contract.” It is not permission to execute anything and must not call runtime, transport, firmware, keyboard, mouse, buzzer, Launch, or recovery services.

Any future actuator adapter requires a separate issue, branch, PR, threat review, tests, hardware acceptance, and explicit user approval.

## 3. Inputs

A gate evaluation receives one immutable snapshot:

- `Intent`: named diagnostic intent, for example `Login`, `Disconnect`, `Game`, or `Targeted`.
- `ObservedState`: classifier output.
- `ObservedAt`: monotonic timestamp of the newest Lux sample.
- `StableSince`: monotonic timestamp at which the current state became stable.
- `Now`: monotonic evaluation timestamp from the same clock.
- `WatchSessionId`: opaque identifier regenerated on every watch start or reconnect.
- `ProfileRevision`: revision/hash of the profile set used by the classifier.
- `ExpectedProfileRevision`: revision currently accepted by the evaluator.
- `ConnectionHealthy`: read-only transport health.
- `CancellationRequested`: caller cancellation state.
- `MaxSampleAgeMs`: configurable freshness limit; proposed default `2000 ms`.
- `RequiredStableMs`: copied from the matched profile; currently `1250 ms` for calibrated profiles.

Wall-clock time must not be used for age or stability calculations.

## 4. Output

The result is immutable:

- `Decision`: `Eligible` or `Denied`.
- `ReasonCode`: one stable machine-readable code.
- `EvaluatedAt`: monotonic evaluation timestamp.
- `WatchSessionId` and `ProfileRevision`: echoed for audit correlation.
- diagnostic age and stability duration.

The result must not contain an executable callback, command, key sequence, transport handle, or mutable runtime reference.

## 5. Fail-closed rules

The evaluator returns `Denied` when any rule below is true, in this precedence order:

1. `Cancelled` — cancellation is requested.
2. `Disconnected` — connection is not healthy.
3. `InvalidTime` — timestamps are missing, from different domains, negative, or ordered impossibly.
4. `StaleSample` — `Now - ObservedAt > MaxSampleAgeMs`.
5. `ProfileChanged` — profile revisions do not match.
6. `UnknownState` — classifier state is Unknown.
7. `InvalidState` — classifier state is Invalid.
8. `AmbiguousState` — classifier state is Ambiguous.
9. `CandidateOnly` — classifier state is Candidate rather than Stable.
10. `NotStableLongEnough` — stable duration is below `RequiredStableMs`.
11. `IntentMismatch` — stable profile does not match the requested intent.

Only a fresh, healthy, revision-matched, sufficiently stable and intent-matched `Stable` observation returns `Eligible`.

Unknown or future enum values must map to `Denied/UnsupportedState`; they must never fall through to Eligible.

## 6. Intent mapping

- Desktop -> Desktop profile.
- Character dashboard -> Character dashboard profile.
- Entering-game loading -> Entering-game loading profile.
- Game -> Game profile.
- Targeted -> Targeted profile.
- Login and Disconnect -> shared Login/DC profile.

The gate does not distinguish Login from Disconnect by Lux. The caller supplies the intent. The historical `Disconnect = one ESC then Login flow` contract remains outside this evaluator and is not executed in Phase 5 design work.

## 7. Session and race rules

- Every watch start and reconnect creates a new `WatchSessionId`.
- A snapshot from an older session is denied even when its Lux value still matches.
- Profile Save/Reset/import increments `ProfileRevision` and invalidates previous observations.
- Stop, disconnect, cancellation, profile mutation, or stale age immediately deny subsequent evaluations.
- Evaluations are idempotent and side-effect-free.
- Concurrent evaluations of the same snapshot must return byte-equivalent decisions.
- No cached Eligible result may outlive its input snapshot.

## 8. Audit contract

A diagnostic log entry may contain:

- decision and reason code;
- intent and observed state;
- sample age and stable duration;
- session ID hash and profile revision hash;
- connection-health and cancellation booleans.

It must not contain secrets, raw keys, executable macro content, personal file paths, or full serial payload dumps by default.

## 9. Acceptance gates

Phase 5 design is accepted only when:

1. Pure evaluator tests cover every deny reason and the single Eligible path.
2. Tests prove no transport/runtime/HID/buzzer dependency is referenced.
3. Race tests cover reconnect, stale transition, profile edit, cancellation, and concurrent evaluation.
4. Hardware acceptance observes decisions only; it sends no command to either board.
5. Static review confirms there is no connection from the evaluator to Macro, Launch, Auto Resume, BEEP, `WLUX`, or `TRGLUX`.
6. The PR remains Draft until the contract and test matrix are explicitly accepted.

## 10. Deferred work

Implementation of the pure evaluator may follow in a separate commit on this phase branch after contract approval. Connecting an actuator is explicitly deferred to a later phase and separate PR.