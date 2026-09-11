# Pro Micro firmware 2.6 — helper-free host USB lifecycle

Based byte-for-byte on the accepted 2.5 mouse/link line except for host-lifecycle telemetry.

The ATmega32U4 USB core is polled for `USBDevice.configured()` and
`USBDevice.isSuspended()`. Debounced state changes are emitted only on the private
Serial1 brain link:

- `EVT|HOSTUSB|UP`
- `EVT|HOSTUSB|SUSPEND`
- `EVT|HOSTUSB|DOWN`

`VER` on Serial1 advertises `HOSTUSB=1`. No Windows executable, service, scheduled
task, startup file, registry entry, or network probe is required. Windows can still
record ordinary restart and USB enumeration events; this feature does not attempt to
hide those operating-system records.

Target: ATmega32U4 Pro Micro 5V/16MHz. Flash using the same ISP procedure as fw 2.5.
