#!/usr/bin/env python3
"""Embed one provisioned USB serial in an Arduino AVR USBCore.cpp copy.

The stock ATmega32U4 core builds iSerial from interface short names, so it is
not a per-device identity. Classroom Studio builds a device-specific core copy
and this strict, idempotent patch makes descriptor 3 return the provisioned
serial directly from flash.
"""
from pathlib import Path
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_avr_usb_serial.py <USBCore.cpp> <serial>")
path = Path(sys.argv[1])
serial = sys.argv[2].strip()
if not re.fullmatch(r"[A-Za-z0-9._-]{1,29}", serial):
    raise SystemExit("serial must be 1..29 ASCII letters, digits, dot, underscore or hyphen")
text = path.read_text(encoding="utf-8")
marker = "AMS_USB_SERIAL_PATCH_V1"
if marker in text:
    expected = f'const u8 STRING_SERIAL[] PROGMEM = "{serial}";'
    if expected not in text:
        raise SystemExit("USBCore.cpp is already provisioned with a different serial")
    print(f"USB serial already provisioned: {serial}")
    raise SystemExit(0)

old_decl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;"
new_decl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\nextern const u8 STRING_SERIAL[] PROGMEM; // AMS_USB_SERIAL_PATCH_V1\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;"
old_value = "const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\n\n#define DEVICE_CLASS"
new_value = f'const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\nconst u8 STRING_SERIAL[] PROGMEM = "{serial}";\n\n#define DEVICE_CLASS'
old_branch = """else if (setup.wValueL == ISERIAL) {
#ifdef PLUGGABLE_USB_ENABLED
 char name[ISERIAL_MAX_LEN];
 PluggableUSB().getShortName(name);
 return USB_SendStringDescriptor((uint8_t*)name, strlen(name), 0);
#endif
 }"""
new_branch = f"""else if (setup.wValueL == ISERIAL) {{
 return USB_SendStringDescriptor(STRING_SERIAL, {len(serial)}, TRANSFER_PGM);
 }}"""
for old, label in ((old_decl, "declaration"), (old_value, "value"), (old_branch, "descriptor branch")):
    if text.count(old) != 1:
        raise SystemExit(f"unsupported USBCore.cpp: expected one {label}, found {text.count(old)}")
text = text.replace(old_decl, new_decl, 1).replace(old_value, new_value, 1).replace(old_branch, new_branch, 1)
path.write_text(text, encoding="utf-8", newline="\n")
print(f"provisioned application USB serial {serial}: {path}")
