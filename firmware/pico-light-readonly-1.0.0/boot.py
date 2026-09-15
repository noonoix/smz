# Classroom Studio — read-only Pico light telemetry USB policy
# No HID device is exposed. One CDC console is used for the read-only endpoint.
import usb_cdc
import usb_hid

try:
    usb_hid.disable()
except Exception:
    pass

try:
    usb_cdc.enable(console=True, data=False)
except Exception:
    # Keep the file safe on CircuitPython variants that already expose console.
    pass
