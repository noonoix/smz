# Phase 6 Hardware Acceptance Readiness Checklist

> **Preparation only. No hardware test has been executed by this checklist.**
>
> This checklist is for the later, separately authorized acceptance pass. It does not authorize Merge, Release, actuator connection, Macro execution, keyboard/mouse/HID output, BEEP, Launch, Recovery or Auto Resume.

## Scope and safety boundary

- [ ] Test only the non-executing authorization diagnostics path.
- [ ] Keep the actuator path absent, disconnected or explicitly disabled for the entire pass.
- [ ] Do not connect this path to `RunEngine`, an execution callback, command transport or actuator bridge.
- [ ] Confirm the operator-facing card visibly says `فقط تشخیصی — بدون اجرا`.
- [ ] Record the test operator, date/time, build commit and hardware identifiers before starting.
- [ ] Define an independent abort operator and stop condition before starting.

## Preconditions

- [ ] PR #174 is still the intended Draft PR and its head is recorded.
- [ ] Windows app build-test is green for the exact head under test.
- [ ] Portable contracts are green for the exact head under test.
- [ ] Sensitive-guard is green for the exact head under test.
- [ ] The downloadable test package is not treated as a release artifact; its intentional skip is understood.
- [ ] The Pico firmware and read-only light telemetry path are identified and version-recorded.
- [ ] A clean baseline serial capture is ready for comparison.
- [ ] No unrelated macro, keyboard, mouse, HID, buzzer or automation process is running.
- [ ] The pipeline workspace is saved or its revision is recorded before the pass.

## Read-only transport baseline

- [ ] Connect only the approved read-only telemetry hardware.
- [ ] Start Light Watch and verify that observed transport is limited to the existing read-only `LUX?` traffic.
- [ ] Confirm there is no outbound Run, Launch, Recovery, Resume, Macro, keyboard, mouse, HID or BEEP command.
- [ ] Confirm the authorization card starts disarmed and does not issue a permit from observation, timer activity or property changes.

## Manual authorization lifecycle

For each selected allowlisted intent, use a fresh Watch session and record the raw reason code after every action:

- [ ] Select only one of: Desktop, Character Dashboard, Loading, Game or Targeted.
- [ ] Confirm Login and Disconnect are not selectable.
- [ ] Press **Arm diagnostics** manually.
- [ ] Confirm the card enters Armed and no execution occurs.
- [ ] Wait for the matching stable diagnostic gate.
- [ ] Press **Issue diagnostic permit** manually.
- [ ] Confirm only the local ledger/card state changes.
- [ ] Confirm the Arm button is disabled while the arm/permit is active.
- [ ] Press **Consume without execution** manually.
- [ ] Confirm the card reports ledger-only consumption and no execution occurs.
- [ ] Confirm a second Consume is denied as `AlreadyConsumed`.
- [ ] Confirm a second Issue requires a new explicit Arm.

## Fail-closed lifecycle checks

For every item below, verify both the visible state and the raw reason code:

- [ ] Stop Watch → revoke with `Disconnected`.
- [ ] Disconnect the board → revoke before asynchronous Watch disposal.
- [ ] Trigger or observe a Watch fault → revoke with `StaleGateResult` before any later action.
- [ ] Reconnect Watch → old session arm/permit cannot be reused.
- [ ] Save or reset a light profile → revoke with `ProfileChanged` before the new revision is accepted.
- [ ] Change the selected intent → revoke the previous arm/permit.
- [ ] Change Pipeline at root level → immediate revoke with `PipelineChanged`.
- [ ] Change a nested pipeline property/tree node → next authorization operation fails closed on revision mismatch.
- [ ] Let the arm expire → Issue is denied with `ArmExpired`.
- [ ] Let the permit expire → Consume is denied with `PermitExpired`.
- [ ] Reuse the same observation identity → Issue is denied with `ObservationAlreadyAuthorized`.
- [ ] Present a denied, candidate, unknown or intent-mismatched gate → Issue is denied.

## Pass criteria

The pass is successful only when all of the following remain true:

- [ ] No Macro, keyboard, mouse, HID, BEEP, Launch, Recovery, Auto Resume or other actuator side effect occurs.
- [ ] Serial output remains limited to the approved read-only telemetry baseline.
- [ ] Every Issue and Consume requires a direct manual button action.
- [ ] Every lifecycle invalidation is visible in the card and has a stable raw reason code.
- [ ] A consumed or revoked permit cannot be reused.
- [ ] Pipeline, profile, session, connection and Watch-fault changes fail closed.
- [ ] The UI never presents a diagnostic permit as an execution permission.

## Immediate stop conditions

Stop the pass immediately and mark it **failed** if any of the following occurs:

- [ ] Any command other than approved read-only telemetry is observed.
- [ ] Any Macro, keyboard, mouse, HID, BEEP, Launch, Recovery or Auto Resume activity occurs.
- [ ] A permit is issued or consumed without the corresponding manual button action.
- [ ] A permit remains usable after disconnect, Watch fault, profile change, intent change or pipeline mismatch.
- [ ] The card loses the `فقط تشخیصی — بدون اجرا` warning or presents a misleading execution state.

## Evidence record

- Build commit: `______________________________`
- PR/branch: `______________________________`
- App version: `______________________________`
- Pico firmware version: `______________________________`
- Hardware identifiers: `______________________________`
- Operator: `______________________________`
- Start/end time: `______________________________`
- Serial baseline artifact: `______________________________`
- UI screenshots/log artifact: `______________________________`
- Result: `PASS / FAIL / NOT RUN`
- Notes and deviations: `______________________________`

## Current status

- **Checklist prepared:** yes
- **Hardware Acceptance executed:** no
- **Actuator enabled:** no
- **Merge/Release authorized:** no
