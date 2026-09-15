# Phase 5 — Read-only Light-Gate Coordinator

Tracking: #166

## Boundary

The coordinator joins classifier snapshots to the already-merged pure gate evaluator. It produces diagnostic `Eligible/Denied` data only.

```text
Live Watch sample -> classifier -> read-only coordinator -> pure gate -> diagnostic result
                                                               X no actuator
```

It does not start Watch, write to the bridge, send board commands, run macros, press keys, move the mouse, beep, launch, recover, or auto-resume.

## Lifecycle

- Every Watch start/reconnect creates a new opaque session ID.
- A deterministic SHA-256 revision is calculated from the complete sorted profile snapshot.
- Candidate timing is retained only inside the active session and matching profile revision.
- Stable timing is inherited from the matching candidate; a missing candidate fails closed by starting stability at the first observed Stable sample.
- Stop clears the active session and returns `Denied/Disconnected`.
- Profile Save/Reset/import changes the revision, clears timing state and returns `Denied/ProfileChanged`.
- Old session and old revision observations cannot mutate timing state.

## Data contract

The coordinator accepts:

- intent;
- classifier result;
- monotonic observation/evaluation times;
- session ID and profile revision attached to the observation;
- connection and cancellation state.

It returns the immutable `LightGateResult`. There is no callback, command, transport handle or runtime reference.

## Current scope

This commit provides the coordinator core and lifecycle contract tests. UI binding remains a separate reviewable step on the same issue; it may display only decision and reason. Actuator integration is not part of this issue.