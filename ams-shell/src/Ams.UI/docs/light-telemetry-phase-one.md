# Light Telemetry — Phase One Implementation

## Implemented

- Added the exact read-only `LUX?` request to the Pico command dispatcher.
- Added a boot-local unsigned `seq` counter. It advances only after a valid BH1750 sample.
- Added deterministic results:
  - `OK|LUX|seq=<n>|lux=<value>|mode=<hires|lowres>|sensor=ok`
  - `ERR|NOSENSOR|LUX`
  - `ERR|I2C|LUX`
  - `ERR|BUSY|LUX`
- Busy is returned while Pico-to-arm mouse traffic is in flight or has a pending coalesced move.
- Invalid, negative and NaN readings are reported as I2C failures and never advance `seq`.
- Existing `LCAL`, `WLUX` and `TRGLUX` branches remain intact and in their original order.

## Output parity

The contract is present in:

- the canonical `PicoFirmwareExporter` template used by normal export;
- the standalone firmware template;
- the accepted `code64f` firmware source.

AutoCycle starts from `PicoFirmwareExporter.Export` and applies its runtime patch afterward, so the telemetry handler is shared by normal and AutoCycle outputs.

## Side-effect boundary

The telemetry helper only reads the sensor and formats a response. It does not call keyboard, mouse, buzzer, calibration, plan control or file-writing paths.

## Validation

`tools/test_light_telemetry_protocol.py` behavior-tests healthy high/low-resolution samples, monotonic sequence values, no sensor, I2C failure, invalid sensor values and both busy conditions. It also pins the legacy light command markers in every maintained source.
