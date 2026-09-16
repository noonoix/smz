# Phase 7 — Guard transition matrix for portable output

This document records the approved relation between the six optical profiles and the Classroom Studio pipeline tabs. Classroom Studio authors and exports the bundle; the portable runtime on the Pico is the component that must apply this policy after the files are copied to `CIRCUITPY`.

## Canonical optical positions and ordered progression

The primary progression is strictly ordered:

| Stage | Optical profile / visible tab | Normal next stage |
|---:|---|---:|
| 1 | `desktop` / `Desktop` | 2 — `login-or-dc` |
| 2 | `login-or-dc` / `Login / DC` | 3 — `character-dashboard` |
| 3 | `character-dashboard` / `Character Dashboard` | 4 — `entering-game-loading` |
| 4 | `entering-game-loading` / `Entering Game / Loading` | 5 — `game` |
| 5 | `game` / `Game` | remain in the game context |

A stable optical match may advance the portable controller only to the next stage in this table. It must not skip a stage or execute the same transition repeatedly while the optical state remains unchanged.

`Resumable` remains a separate workspace and is not part of the optical progression.

## DC fallback

`login-or-dc` is one optical calibration profile, not two profiles. The portable runtime/pipeline context distinguishes Login from DC.

When the runtime observes the DC optical signature at any active in-game point, it must:

1. leave the current progression context;
2. fall back to stage 2 (`Login / DC`);
3. select the independent `DC` portable context;
4. execute the approved stage-2 DC recovery Steps once;
5. resume the normal ordered progression from stage 2 through stages 3, 4 and 5.

The DC fallback applies to stages 3–5 and to the Targeted side-state. It must not create a second calibration record or silently reuse an unrelated Login action.

## Targeted side-state

`targeted` / `Targeted` is a separate optical position with its own Steps. It is not stage 6 and does not replace any stage in the ordered 1–5 path.

While the portable runtime is in the game context, a stable Targeted match may preempt the current game observation:

1. select the `Targeted` tab/context;
2. execute its target-specific Steps once;
3. leave the side-state and return to the `Game` context;
4. require a fresh stable optical state before any Targeted or Game transition is executed again.

If the DC signature is detected while Targeted is active, DC has priority and the runtime falls back to stage 2 instead of completing the Targeted side-state first.

## Portable execution guards

The exported manifest/plan and its Pico runtime must enforce all of the following:

- stable-state debounce before selecting a transition;
- one-shot execution for each stable optical-state entry;
- rearming only after the optical state changes and becomes stable again;
- independent Login/DC context selection;
- fail-closed behavior for a missing mapping, stale calibration revision, changed pipeline revision or Stop;
- no execution from duplicate Guard events or from a bundle mutation that was not revalidated;
- atomic bundle publication so a partially exported plan can never boot as a valid runtime.

The seven visible tabs and this matrix do not authorize automatic execution until those boundaries are implemented in the portable bundle and covered by portable-runtime tests. Physical hardware acceptance remains separate.
