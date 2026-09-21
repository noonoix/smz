# Plan Engine migration to the streaming Guard runtime

Status: active migration; Phase 0 and Phase 1 implemented

## Goal

Remove `plan_engine.py` from the Combined Guard execution path without losing any exported step, timing range, control-flow behavior, Human Input parameter, Guard transition, Pause/Resume/Stop behavior, or fail-safe cleanup.

The standalone portable/simulator engine remains available until parity is proven. Combined Guard must not import it, even lazily.

## Ownership after migration

- Pico: Guard, route selection, streaming control flow, Keyboard HID, loops, packages, includes, Pause/Resume/Stop and restart orchestration.
- Pro Micro: Mouse HID, complete mouse humanization and sound sensing/trigger actions.
- Guard: sole light-state authority. `WLIGHT`/`IFLUX` are rejected in Guard routes and migrated to state routes.

## Non-negotiable invariants

1. Route size must not determine Pico RAM usage.
2. No hidden fixed timing, rounding, clamping, swapping or discarded Humanization field.
3. Random ranges remain inclusive where the application contract is inclusive.
4. Unknown or not-yet-migrated commands fail before hardware action.
5. State transition, Stop and failure release every Pico key and every Pro Micro mouse button.
6. Debug output never contains TYPE text.
7. Targeted remains a repeatable side-state; Resumable and Restart remain first-class routes.
8. A phase cannot remove its old implementation until golden parity and hardware acceptance pass.

## Phase 0 — inventory and freeze

Deliverables:

- Freeze the PLAN|2/3 operation inventory and ownership matrix.
- Keep existing simulator goldens as the behavioral oracle.
- Add migration tests that reject accidental `plan_engine` imports in Combined Guard.

Operation groups:

- Metadata: `PLAN`, `SCREEN`, `SPEED`.
- Timing/control: `DELAY`, `LOOP`, `LOOPTIME`, `ENDLOOP`, `LABEL`, `GOTO`, `INCLUDE`.
- Keyboard: `KEY`, `KDOWN`, `KUP`, `TYPE`.
- Mouse: `RMOUSE`, `MOVETO`, `CLICK`, `WHEEL`.
- Sound: `WSND`, `TRGSND`, `IFSND`.
- Containers: `RPKG`, `PKGITEM`, `ENDPKG`, `PGROUP`, `PARITEM`, `ENDPAR`.
- Local device: `BEEP`, `RAW`.
- Legacy light: `WLIGHT`, `IFLUX`, `STATELOOP`; these are not executable inside Guard routes.

Acceptance: every emitted operation has exactly one migration owner and no operation silently falls back to the old engine.

## Phase 1 — sever the Combined Guard import

- Remove the deferred `plan_engine` proxy from packaged `code.py`.
- Remove `import plan_engine` from packaged `combined_guard_runtime.py`.
- Keep the existing streaming runner as the only `Combined.route` implementation.
- Unsupported operations remain fail-closed.

Acceptance:

- Importing Combined Guard cannot load `plan_engine`.
- Current `PLAN/SCREEN/SPEED/DELAY/BEEP/LOOP/LOOPTIME/ENDLOOP/KEY/KDOWN/KUP` routes keep working.
- Heap checkpoints are recorded before and after route open.

## Phase 2 — keyboard parity on Pico

- Finish `KEY`, `KDOWN`, `KUP` hardware acceptance.
- Implement streaming `TYPE` without materializing a command list.
- Preserve key-hold, inter-key, word, punctuation and think pauses.
- Preserve typo cadence, QWERTY-neighbor generation, correction delay and Backspace.
- Make text payload logging impossible by construction.

Acceptance: golden seeded plans match the existing planner’s decisions and timing bounds; Stop/state-change leaves no held key.

## Phase 3 — full mouse humanization on Pro Micro

- Add versioned framed commands for `RMOUSE` and `MOVETO` carrying every existing parameter.
- Port curve, acceleration/deceleration, speed profile, overshoot, correction, mid-pause, long idle and landing distribution to Pro Micro.
- Keep execution non-blocking and HALT-abortable.
- Pico streams only bounded commands and pumps Guard/buttons/UART while waiting.

Acceptance: seeded path/timing golden vectors match the existing HumanMouse contract within explicitly documented numeric tolerances; no linear fallback exists.

## Phase 4 — sound and immediate mouse operations

- Stream `CLICK`, `WHEEL`, `WSND`, `TRGSND` to Pro Micro.
- Implement `IFSND` branch selection on Pico without loading a tree.
- Preserve inclusive reaction/hold ranges and timeout semantics.

Acceptance: all operations remain HALT-abortable; timeout and detection branches are deterministic under the simulator clock.

## Phase 5 — bounded streaming control flow

- Add bounded frame records for IF, loop, package and parallel blocks.
- Build only small offset indexes for `LABEL/GOTO` and container boundaries; never retain route text or command trees.
- `INCLUDE` opens child files on demand with cycle detection and depth cap four.
- `RPKG` redraws every pass.
- `PGROUP` uses cooperative one-operation round-robin and keeps Guard polling active.

Acceptance: RAM growth is bounded by nesting depth and branch count, not file length.

## Phase 6 — remove legacy payload and close migration

- Remove `plan_engine.py` from Combined Guard runtime files, expected inventory, README and hashes.
- Keep it only for standalone simulator/legacy portable packages until those have a separate deprecation decision.
- Run all portable, Windows, Pico, Plan2, security and collector checks.
- Run hardware acceptance on COM31 for Keyboard, mouse, sound, Stop, Pause/Resume, state transition and Restart.

Acceptance: Combined Guard boots and completes the full golden project with no `plan_engine` file present and with greater or equal free heap at every checkpoint.

## Rollout gates

Each phase lands separately. A failing phase is reverted without enabling a fallback to the old engine. The next product feature (`TYPE` expansion beyond parity, new Humanization, etc.) starts only after Phase 6 hardware acceptance.
