# Phase 6 — explicit light execution authorization boundary

## Status

Design and pure-contract stage only. This document does **not** activate an actuator and does not connect `LightGateResult` to `RunEngine`, Bridge, HID, Launch, Recovery, Auto Resume, buzzer, Pico or Pro Micro.

Issue: #170

## Why this boundary exists

`LightGateResult.Eligible` is diagnostic evidence that one requested `LightExecutionIntent` matched a fresh, stable light-state observation. It is not consent, not an execution command and not a reusable capability.

The future execution path must therefore contain a separate authorization boundary:

`classification → diagnostic gate → explicit authorization → actuator adapter`

The diagnostic gate remains pure and actuator-free. The authorization boundary may produce a short-lived, one-shot permit. Consuming a permit only verifies authorization; the actuator adapter remains a later, separately reviewed component.

## Non-negotiable invariants

1. Default is deny.
2. `Eligible` alone never authorizes execution.
3. Authorization requires an explicit, current arm lease for one allowlisted intent.
4. An arm lease and a permit are bound to the current process generation, Watch session, profile revision and pipeline revision.
5. A permit is bound to one observation identity and one intent.
6. A permit expires using caller-owned monotonic time; wall-clock time is never trusted.
7. A permit is consumable at most once.
8. Validation and consume are one atomic ledger operation; there is no check-then-act window inside the boundary.
9. Stop, disconnect, cancellation, stale data, profile change, Watch reconnect, pipeline edit, disarm and process restart revoke outstanding permits.
10. `Login` and `Disconnect` remain distinct intents even though both use the `login-or-dc` profile. Light alone must never choose between them.
11. Unknown enum values and malformed identifiers fail closed.
12. No permit contains a callback, delegate, runtime reference, transport handle or executable payload.

## Vocabulary

### Arm lease

A time-bounded statement of explicit operator intent. It contains:

- `ArmGenerationId`
- one `LightExecutionIntent`
- `ProcessGenerationId`
- `WatchSessionId`
- `ProfileRevision`
- `PipelineRevision`
- `ArmedAt`
- `ExpiresAt`

Arming is independent of light classification. The implementation in this phase does not provide an Arm button; it only defines and tests the contract.

### Authorization request

An immutable snapshot containing:

- the arm lease
- the complete `LightGateResult`
- the requested `LightExecutionIntent`
- `ObservationId` supplied by the coordinator owner
- expected Watch session and profile revision
- expected pipeline revision
- monotonic `Now`
- cancellation and connection-health flags

### Permit

Opaque immutable data issued only after every check passes:

- random `PermitId`
- `ArmGenerationId`
- requested intent
- process, Watch session, profile and pipeline revisions
- observation identity
- `IssuedAt`
- `ExpiresAt`

A permit carries identity only. It carries no command or action.

### Ledger

A process-local state owner that records arm generations, outstanding permit IDs and terminal permit states. Process restart creates a new generation and makes old leases and permits invalid by construction.

## State model

Arm lifecycle:

`Disarmed → Armed → Revoked | Expired`

Permit lifecycle:

`None → Issued → Consumed | Revoked | Expired`

Terminal states never transition back. Re-arming creates a new arm generation; it does not revive an older lease or permit.

## Issue checks

A permit may be issued only when all conditions are true, in fail-closed order:

1. request and identifiers are structurally valid;
2. cancellation is not requested;
3. connection is healthy;
4. arm lease exists and is not revoked or expired;
5. arm intent equals requested intent;
6. process generation matches;
7. Watch session matches and is active;
8. profile revision matches;
9. pipeline revision matches;
10. observation identity is non-empty and not previously used to issue a permit;
11. gate decision is `Eligible` with reason `EligibleStableMatch`;
12. gate Watch session and profile revision equal the request;
13. gate age remains within the authorization freshness budget;
14. requested intent is allowlisted by caller policy.

Any failure returns a stable denial reason and creates no permit.

## Atomic consume checks

`TryConsume` runs under one ledger critical section. It returns an immutable verification result, never an action.

It verifies:

- permit ID exists and is currently `Issued`;
- cancellation is not requested;
- connection is healthy;
- monotonic `Now` is valid and no later than `ExpiresAt`;
- process, Watch session, profile revision and pipeline revision still match;
- arm generation is still active;
- requested intent exactly matches the permit;
- permit has not already been consumed, revoked or expired.

On success, the ledger marks it `Consumed` before returning success. A second consume must return `AlreadyConsumed`.

## Revocation events

The owner must call `RevokeAll` before or as part of handling:

- Watch Stop
- board disconnect
- Watch reconnect/session replacement
- profile Save/Reset/import
- pipeline edit, load or tab-plan replacement
- explicit disarm
- cancellation
- application shutdown

The API also receives current generation/revision values at issue and consume time, so a missed notification still fails closed when identities no longer match.

## Proposed stable reason codes

Issue denials:

- `NotArmed`
- `ArmExpired`
- `ArmIntentMismatch`
- `GateDenied`
- `GateReasonMismatch`
- `Cancelled`
- `Disconnected`
- `InvalidTime`
- `StaleGateResult`
- `ProcessGenerationChanged`
- `WatchSessionChanged`
- `ProfileChanged`
- `PipelineChanged`
- `ObservationMissing`
- `ObservationAlreadyAuthorized`
- `IntentNotAllowed`
- `MalformedRequest`

Consume denials:

- `PermitUnknown`
- `PermitExpired`
- `PermitRevoked`
- `AlreadyConsumed`
- `PermitIntentMismatch`
- `Cancelled`
- `Disconnected`
- `InvalidTime`
- `ProcessGenerationChanged`
- `WatchSessionChanged`
- `ProfileChanged`
- `PipelineChanged`
- `ArmRevoked`

Success reasons:

- `PermitIssued`
- `PermitConsumed`

## Intent policy

The boundary treats every `LightExecutionIntent` as data and never maps it to commands.

Special rule: `Login` and `Disconnect` cannot be selected from the shared `login-or-dc` light profile. A caller must already know the entry reason from independent state. If that independent reason is absent, authorization is denied.

A later actuator PR must define a narrow allowlist. No intent is implicitly allowed by this document.

## Threat matrix

| Threat | Required behavior |
|---|---|
| Replay of a consumed permit | `AlreadyConsumed` |
| Replay after restart | process-generation mismatch |
| Double-click/double event | one issue per observation and one consume per permit |
| TOCTOU between check and consume | atomic ledger validation/consume |
| Wall-clock rollback | irrelevant; monotonic time only |
| Watch reconnect | old session denied and outstanding permits revoked |
| Profile Save with same values | arm/permits revoked by lifecycle event even if canonical hash repeats |
| Pipeline edit | pipeline revision mismatch and revocation |
| Gate result copied to another intent | intent mismatch |
| Shared Login/DC profile | caller-supplied independent reason required |
| UI binding race | UI has no authority; ledger identities decide |
| Disconnect after issue | consume denied and permits revoked |
| Cancellation after issue | consume denied and permits revoked |
| Malformed/unknown enum | deny, no exception-driven success path |
| Concurrent consumers | one success maximum |
| Permit ID guessing | unknown ID denied; IDs are random and non-sequential |

## Audit contract

Audit records may contain permit ID, intent, revisions, monotonic timestamps and stable reason codes. They must not contain executable payloads, secrets, raw keyboard content or authentication material.

Required events:

- arm created/revoked/expired
- permit issue denied/issued
- permit consume denied/consumed
- bulk revocation with lifecycle reason

Audit is observational. Audit failure must never convert denial to success.

## Contract-test matrix

The pure contract implementation must cover at least:

- eligible + valid arm → one permit
- eligible without arm → deny
- gate denied → deny
- gate reason inconsistent with decision → deny
- expired arm and expired permit
- stale gate result
- cancellation and disconnect at issue and consume
- process/session/profile/pipeline mismatch
- observation replay
- double consume
- concurrent consume, exactly one success
- explicit revocation
- restart generation invalidation
- same-value profile Save revocation
- Login/DC independent-reason requirement
- unknown intent/reason values
- invalid monotonic ordering

## Integration sequence

1. This PR: design, pure authorization ledger and contract tests only.
2. Separate PR: read-only UI for arm/permit diagnostics, still no actuator.
3. Hardware observation: verify arm, issue, expiry and revoke displays without commands.
4. Separate threat-reviewed PR: one narrowly scoped actuator adapter, disabled by default and protected by an explicit feature gate.

No later step is implied or authorized by acceptance of this document.
