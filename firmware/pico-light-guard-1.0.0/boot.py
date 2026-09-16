# Classroom Studio Phase 7 — isolated light Guard USB policy
# Guard firmware exposes only the USB serial console. It has no HID, UART or actuator path.
import usb_cdc
import usb_hid

try:
    usb_hid.disable()
except Exception:
    pass

try:
    usb_cdc.enable(console=True, data=False)
except Exception:
    # Keep the safe console policy on CircuitPython variants that already expose console.
    pass
