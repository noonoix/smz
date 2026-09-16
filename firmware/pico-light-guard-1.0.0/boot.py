# Combined Pico firmware USB configuration.
# HID remains enabled for Portable Steps; CDC data is the Classroom Studio channel.
import usb_cdc
import usb_hid

usb_cdc.enable(console=True, data=True)
# usb_hid is intentionally not disabled: Pico HID is the keyboard path.
