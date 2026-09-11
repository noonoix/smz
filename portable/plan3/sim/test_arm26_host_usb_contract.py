#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[3]
s = (root / 'firmware/arm26/ams_board26.ino').read_text()
base = (root / 'firmware/arm25/ams_board25.ino').read_text()
assert '#define FW_VER   "2.6"' in s
assert 'USBDevice.configured()' in s and 'USBDevice.isSuspended()' in s
assert 'HOST_USB_DEBOUNCE_MS 120UL' in s
assert 'EVT|HOSTUSB|' in s and 'HOSTUSB=1' in s
assert 'poll_host_usb();' in s
assert s.index('poll_host_usb();') < s.index('if (serial1_line_ready())', s.index('void loop()'))
for state in ('UP', 'SUSPEND', 'DOWN'):
    assert 'F("%s")' % state in s
assert s.count('{') == s.count('}')
assert s.count('(') - s.count(')') == base.count('(') - base.count(')')
print('arm26 host USB contract: 12 passed, 0 failed')
