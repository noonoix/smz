# Phase 6 — non-executing authorization diagnostics

## Status

Design and implementation boundary for Issue #172. This surface mutates only process-local authorization state. It never runs a pipeline, invokes a callback, writes to a bridge or sends a board command.

## User-visible purpose

The existing Status page already shows the pure diagnostic gate. The next section lets an operator exercise the authorization contract manually:

1. choose one safe diagnostic intent;
2. press **Arm diagnostics**;
3. wait for the existing gate to become `EligibleStableMatch` for that exact intent;
4. press **Issue diagnostic permit**;
5. optionally press **Consume without execution**;
6. observe expiry or revoke.

Every label must include `فقط تشخیصی — بدون اجرا` so a permit cannot be mistaken for an active automation setting.

## Initial intent allowlist

The UI exposes only:

- Desktop
- CharacterDashboard
- EnteringGameLoading
- Game
- Targeted

`Login` and `Disconnect` are intentionally absent. Both share the same `login-or-dc` profile and require an independent entry reason that the light sensor cannot provide.

## No automatic issue or consume

A stable light observation does not automatically issue a permit. Issue and consume each require a separate explicit button press. This keeps the diagnostic surface reviewable and prevents a UI update, timer or property-change event from becoming an execution trigger.

No command named Run, Launch, Recovery, Resume, Macro or Execute is referenced by this feature.

## Pipeline revision

A constant or placeholder pipeline revision is forbidden. At arm, issue and consume time the view model must:

1. capture the current `PipelineWorkspace` using the existing lossless serializer;
2. serialize the complete workspace in its canonical tab order;
3. compute SHA-256 over UTF-8 bytes;
4. compare the exact revision with the one bound into the arm/permit.

The revision includes all five tabs and all step fields. Any New/Open/import/edit/undo/redo/tab mutation therefore fails closed at the next authorization operation even if an explicit notification was missed.

Mutating operations should additionally call revoke immediately where practical; identity comparison remains the backstop.

## Observation identity

For the current PC-side Watch path the observation identity is:

`<watch-session-id>:<profile-revision>:<LightChartVersion>`

`LightChartVersion` advances only after a completed typed sample updates the chart. It is combined with the random Watch session and profile revision, so restart, reconnect and profile change cannot replay an identity.

## Controller responsibilities

A new non-UI controller owns:

- one `LightExecutionAuthorizationLedger`;
- selected allowlisted intent;
- current arm lease;
- current permit;
- immutable display snapshot and stable reason code;
- manual Arm, Issue, Consume and Revoke methods.

Every method receives caller-owned monotonic time and current session/profile/pipeline identities. The controller has no WPF, `IBoardBridge`, `RunEngine`, delegate, event or command payload dependency.

## View-model responsibilities

The MainViewModel adapter:

- maps the five display labels to allowlisted intents;
- supplies current `LightGateResult` from the read-only coordinator;
- computes pipeline revision on every Arm/Issue/Consume operation;
- supplies observation identity from session/revision/chart version;
- publishes display strings and button availability;
- revokes on Watch Stop, reconnect, profile Save/Reset/import and connection loss.

The adapter must not call `TryConsume` from a property-change handler. Consume is manual only.

## UI layout

Insert one card below the existing gate decision cards:

- warning: `فقط تشخیصی — هیچ Macro یا Launch اجرا نمی‌شود`
- intent ComboBox
- Arm diagnostics button
- Issue diagnostic permit button
- Consume without execution button
- Revoke button
- state text
- raw reason code in ToolTip
- short permit ID prefix and remaining lifetime for diagnosis only

Buttons use distinct neutral styling. No button uses the app's Run, Launch or danger styles.

## Lifecycle rules

| Event | Required result |
|---|---|
| Watch off | revoke; `Disconnected` |
| board disconnect | revoke; `Disconnected` |
| Watch reconnect | new session; old arm and permit revoked |
| profile Save/Reset/import | revoke before accepting new revision |
| pipeline edit | revision mismatch at next operation; immediate revoke where notified |
| selected intent change | revoke old arm and permit |
| app restart | new process generation; old identities impossible |
| arm timeout | issue denied `ArmExpired` |
| permit timeout | consume denied `PermitExpired` |
| gate Candidate/Unknown/Denied | issue denied `GateDenied` |
| gate intent mismatch | issue denied `GateReasonMismatch` |
| repeated issue for one sample | `ObservationAlreadyAuthorized` |
| repeated consume | `AlreadyConsumed` |

## Logging

Diagnostic log lines use the prefix `light auth diagnostic:` and include only:

- operation
- allowlisted intent
- stable reason code
- short permit ID prefix

They never include pipeline contents, raw key data, secrets or executable payloads.

## Contract tests

The controller and adapter tests must cover:

- exact initial intent allowlist and Login/DC exclusion;
- Arm requires active Watch and healthy connection;
- Issue requires same intent and `EligibleStableMatch`;
- observation identity advances with chart version;
- pipeline revision is deterministic and changes on any tab/tree mutation;
- issue is manual and never happens from observation alone;
- consume is manual and returns display state only;
- Stop/disconnect/reconnect/profile change/intent change revoke;
- expiry and replay reason codes are visible;
- no `IBoardBridge`, `RunEngine`, delegate or execution event exists;
- UI install retries when the Status visual tree starts collapsed.

## Hardware acceptance

Use a release build on the real Pico and confirm:

1. Arm/Issue/Consume change only the authorization card.
2. serial output remains the existing read-only `LUX?` traffic.
3. no Macro, keyboard, mouse, buzzer, Launch, Recovery or Auto Resume occurs.
4. Stop, reconnect and profile Save revoke immediately.
5. pipeline edit prevents issue/consume until re-armed.

This acceptance cannot authorize a later actuator. An actuator remains a separate, disabled-by-default, threat-reviewed Issue and PR.
