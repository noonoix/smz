# Classroom Studio — read-only Pico light telemetry USB policy
# No HID device is exposed. Only the USB CDC data channel is enabled.
import usb_cdc
import usb_hid

try:
    usb_hid.disable()
except Exception:
    pass

try:
    usb_cdc.enable(console=False, data=True)
except Exception:
    # Keep the file safe on CircuitPython variants that already expose CDC data.
    pass
