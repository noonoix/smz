# Human Input Contract v1

Status: initial executable keyboard slice

## Non-negotiable rules

- Pico owns Keyboard HID, Guard state, route orchestration, loops, Pause/Resume and Stop.
- Pro Micro owns Mouse HID and the audio sensor.
- Keyboard and mouse execution remain independent so typing cannot stall or pixel-step the mouse path.
- Humanization parameters are never silently rounded, clamped, swapped or discarded. Migration must report any incompatible legacy value.
- Guard is the only light-state authority. `waitForLight` is legacy in Guard routes and must not be emitted as an in-route wait.
- Route execution is streaming from flash; the number of route lines must not determine RAM usage.
- Unknown commands and unsupported key codes fail closed.
- Stop, state transition and route failure release every held keyboard key.
- Debug events may report operation names, virtual-key numbers and timings, but never typed text.

## Keyboard instruction slice 1

### `KEY`

```text
KEY|combo=<vk>[+<vk>...]|hold=<min_ms>,<max_ms>
```

- Executes one keyboard chord on Pico.
- All keys are pressed in listed order and released in reverse order.
- The hold time is sampled inclusively from the exact exported range.
- `hold` is optional and defaults to zero milliseconds.
- Pause/Resume, Stop, USB polling, Pro Micro pumping and Guard state polling remain active while holding.

### `KDOWN` / `KUP`

```text
KDOWN|<vk>
KUP|<vk>
```

- Preserve explicit key state across subsequent streamed instructions.
- A route exit always releases remaining held keys as a safety invariant.

### Supported virtual keys

The first slice supports A-Z, 0-9, F1-F12, Enter, Escape, Backspace, Tab, Space, punctuation keys, arrows, navigation keys, lock keys, Print Screen, Pause/Break, numpad keys and left/right Shift, Ctrl, Alt and Windows modifiers.

## Deferred slices

- `TYPE` with exact key-hold, inter-key, word, punctuation and think-pause ranges.
- Typo cadence, QWERTY-neighbor mistake generation and Backspace correction timing.
- Mouse commands remain deferred until the existing humanized Pro Micro engine and its full profile parameters are wired without simplification.

## Acceptance criteria for slice 1

- `KEY`, `KDOWN` and `KUP` execute without importing the full `plan_engine`.
- No text payload is written to Collector/debug logs.
- A held key is released after Stop, state change, normal route completion or exception.
- GP3 Pause/Resume and GP4 Stop remain responsive during a ranged key hold.
- Existing BEEP, DELAY and LOOP/LOOPTIME behavior remains unchanged.
- The runtime patch is idempotent and Python syntax-valid.
