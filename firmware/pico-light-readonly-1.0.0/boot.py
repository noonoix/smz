# Classroom Studio — read-only Pico light telemetry USB policy
# No HID device is exposed. CDC is used only for the read-only endpoint.
import usb_cdc
import usb_hid

try:
    usb_hid.disable()
except Exception:
    pass

try:
    # Keep both CDC channels available so the endpoint can be diagnosed even
    # when CircuitPython enumerates data and console as separate COM ports.
    usb_cdc.enable(console=True, data=True)
except Exception:
    # Keep the file safe on CircuitPython variants that already expose CDC.
    pass
