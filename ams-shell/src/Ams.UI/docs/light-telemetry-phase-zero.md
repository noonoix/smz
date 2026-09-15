# Light Telemetry and Status — Phase Zero Contract

## Scope

This contract starts the Status/Live Watch upgrade. Phase zero defines behavior before implementation. It does not change Pipeline execution, `WLUX`, `TRGLUX`, `LCAL`, Launch, Auto Resume, or the portable plan format.

## Architectural boundary

- Classroom Studio is the authoring, calibration, testing and export environment.
- Pico remains the execution brain for keyboard, BH1750 light sensing and portable plans.
- Pro Micro remains the mouse and sound-sensor arm over UART.
- Live Watch is read-only. It must never press a key, start a plan, stop a plan, sound the buzzer, or overwrite calibration.
- `WLUX` remains the blocking plan operation, `TRGLUX` remains the armed reaction, and `LCAL` remains calibration sampling.

## Firmware telemetry protocol

### Request

```text
LUX?
```

### Successful response

```text
OK|LUX|seq=42|lux=1284.7|mode=hires|sensor=ok
```

Fields:

- `seq`: monotonically increasing unsigned sample sequence for the current boot.
- `lux`: finite non-negative decimal value using `.` as decimal separator.
- `mode`: `hires` or `lowres`.
- `sensor`: `ok` in a successful sample.

The Windows receive time is authoritative. Pico real time is deliberately excluded because the current hardware has no reliable RTC.

### Errors

```text
ERR|NOSENSOR|LUX
ERR|I2C|LUX
ERR|BUSY|LUX
```

Unknown or malformed fields are rejected by the typed parser and remain visible in the raw serial log.

## Live Watch policy

- Supported intervals: 100, 250, 500 and 1000 ms.
- Default interval: 250 ms.
- The effective interval is clamped to the selected BH1750 conversion mode.
- Only one telemetry request may be in flight. Polls never overlap or queue.
- Default smoothing is a median of the latest five valid samples.
- The chart keeps a 60-second time window with a hard ceiling of 600 samples.
- Watch stops safely on disconnect, bridge replacement and application exit.
- A running macro does not automatically stop Watch; telemetry is low priority and a busy response skips that sample without blocking execution.

## Health and stale policy

A valid sample becomes stale when:

```text
sample age > max(2000 ms, 3 × effective interval)
```

Health states:

- Healthy
- No sensor
- No data
- Stale
- Pico disconnected
- I2C error
- Busy/skipped

Stale, missing and error samples are not valid inputs to Light State classification.

## Statistics

The UI computes Min, Max, Average and Spread from valid samples in the active 60-second window. Invalid, stale and rejected samples are excluded. Clearing the chart resets these statistics only; it does not change firmware or calibration.

## Light State profile

Light State profiles are separate from executable steps. Each state has:

- stable ID
- display name
- enabled flag
- minimum and maximum Lux
- required stable duration
- hysteresis in Lux

Rules:

- Entry requires continuous membership for the configured stable duration.
- Exit uses hysteresis to avoid boundary flicker.
- Overlapping enabled ranges produce `Unknown`; source order must not silently choose a winner.
- Outside all ranges produces `Unknown`.
- Missing, stale or erroneous telemetry produces `Invalid`.
- Confidence is display-only and must not trigger execution.

Phase four may offer a one-way proposal generated from existing `Wait For Light` steps, but profiles do not directly reuse mutable Step instances.

## Calibration boundary

Calibration duration is user-selectable. Calibration displays collected Min, Max, Average and Spread and proposes values. It must not overwrite `luxCenter`, `luxTolerance` or a Light State profile without an explicit user action.

## Delivery phases

1. Firmware protocol and regression tests; no XAML changes.
2. Typed Bridge API and cancellation-safe Watch service; no Status UI dependency.
3. Independent Status tab with connection cards, Live Watch, chart and statistics.
4. Light State profiles and classifier.
5. Software and physical BH1750 acceptance.
6. Visual review, artifact verification, green CI and release.

## Acceptance gates

### Phase one

- `LUX?` returns a typed healthy sample when BH1750 is present.
- Missing sensor, I2C error and busy behavior are deterministic.
- Existing `WLUX`, `TRGLUX` and `LCAL` tests remain green.
- Normal Pico export and AutoCycle export preserve the same telemetry contract.
- No UI/XAML change is included.

### Phase two

- Parser tests cover valid, malformed, missing, timeout and duplicate-sequence responses.
- Polls cannot overlap.
- Cancellation and disconnect leave no background operation running.
- Stale state is deterministic under a fake clock.

### Phase three

- UI states cover connected, disconnected, no sensor, no data, stale and I2C error.
- Watch has no side effects while a macro is running.
- RTL and narrow-window layouts have no clipping or horizontal overflow.

### Hardware acceptance

- Real BH1750 samples continuously in both modes.
- Disconnect/reconnect recovers without restarting Classroom Studio.
- Two calibrated light states can be entered and exited without flicker.
- Closing Classroom Studio does not impair an already-exported portable Pico plan.
