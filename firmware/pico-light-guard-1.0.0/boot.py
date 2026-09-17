# Combined Pico firmware USB and filesystem configuration.
# HID remains enabled for Portable Steps; CDC data is the Classroom Studio channel.
import board
import digitalio
import storage
import usb_cdc
import usb_hid

# Calibration must atomically persist both Guard JSON files and SHA256SUMS.
# In normal operation CircuitPython owns the filesystem; CIRCUITPY remains
# visible to the host but read-only. Hold GP3 during boot for maintenance mode,
# which leaves the default host-writable/runtime-read-only mount unchanged.
_maintenance = digitalio.DigitalInOut(board.GP3)
_maintenance.switch_to_input(pull=digitalio.Pull.UP)
if _maintenance.value:
    storage.remount("/", readonly=False)
_maintenance.deinit()

usb_cdc.enable(console=True, data=True)
# usb_hid is intentionally not disabled: Pico HID is the keyboard path.
