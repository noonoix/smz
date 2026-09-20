#!/usr/bin/env python3
"""Patch Arduino AVR USBCore so USB_SERIAL can supply a fixed application serial.

The stock ATmega32U4 core builds iSerial from PluggableUSB interface short names,
which is not a per-device identity. Classroom Studio provisions one serial per
board, so production builds define USB_SERIAL and this patch makes descriptor 3
return that exact value from flash. The patch is strict and idempotent.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_avr_usb_serial.py <USBCore.cpp>")
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "AMS_USB_SERIAL_PATCH_V1"
if marker in text:
    print(f"USB serial patch already present: {path}")
    raise SystemExit(0)

old_decl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;"
new_decl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\n#ifdef USB_SERIAL\nextern const u8 STRING_SERIAL[] PROGMEM; // AMS_USB_SERIAL_PATCH_V1\n#endif\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;"

old_value = "const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\n\n#define DEVICE_CLASS"
new_value = "const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\n#ifdef USB_SERIAL\nconst u8 STRING_SERIAL[] PROGMEM = USB_SERIAL;\n#endif\n\n#define DEVICE_CLASS"

old_branch = """else if (setup.wValueL == ISERIAL) {
#ifdef PLUGGABLE_USB_ENABLED
 char name[ISERIAL_MAX_LEN];
 PluggableUSB().getShortName(name);
 return USB_SendStringDescriptor((uint8_t*)name, strlen(name), 0);
#endif
 }"""
new_branch = """else if (setup.wValueL == ISERIAL) {
#ifdef USB_SERIAL
 return USB_SendStringDescriptor(STRING_SERIAL, strlen(USB_SERIAL), TRANSFER_PGM);
#elif defined(PLUGGABLE_USB_ENABLED)
 char name[ISERIAL_MAX_LEN];
 PluggableUSB().getShortName(name);
 return USB_SendStringDescriptor((uint8_t*)name, strlen(name), 0);
#endif
 }"""

for old, label in ((old_decl, "declaration"), (old_value, "value"), (old_branch, "descriptor branch")):
    if text.count(old) != 1:
        raise SystemExit(f"unsupported USBCore.cpp: expected one {label}, found {text.count(old)}")
text = text.replace(old_decl, new_decl, 1).replace(old_value, new_value, 1).replace(old_branch, new_branch, 1)
path.write_text(text, encoding="utf-8", newline="\n")
print(f"patched application USB serial support: {path}")
