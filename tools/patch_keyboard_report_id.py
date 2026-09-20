#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old_send = '''    def _send(self):
        self.device.send_report(self.report)
'''
previous_send = '''    def _send(self):
        try:
            # CircuitPython's standard keyboard descriptor uses report ID 1.
            self.device.send_report(self.report, 1)
        except TypeError:
            # Compatibility with older one-argument Device.send_report builds.
            self.device.send_report(self.report)
'''
current_send = '''    def _send(self):
        try:
            # Standard descriptors use report ID 1, but some board builds expose
            # the optional argument while raising NotImplementedError at runtime.
            self.device.send_report(self.report, 1)
        except (TypeError, NotImplementedError):
            # A single-report keyboard can infer its only report ID.
            self.device.send_report(self.report)
'''
if previous_send in s:
    s = s.replace(previous_send, current_send, 1)
elif old_send in s:
    s = s.replace(old_send, current_send, 1)
elif current_send not in s:
    raise SystemExit("missing keyboard send-report anchor")

old_keys = '''            if code in self.report[2:]:
                continue
            for index in range(2, 8):
                if self.report[index] == 0:
                    self.report[index] = code
                    break
            else:
                raise ValueError("USB HID keyboard supports at most six simultaneous keys")
'''
new_keys = '''            # Do not use ``code in self.report[2:]`` here. On the target
            # CircuitPython build bytearray containment raises NotImplementedError.
            duplicate = False
            for index in range(2, 8):
                if self.report[index] == code:
                    duplicate = True
                    break
            if duplicate:
                continue
            for index in range(2, 8):
                if self.report[index] == 0:
                    self.report[index] = code
                    break
            else:
                raise ValueError("USB HID keyboard supports at most six simultaneous keys")
'''
if old_keys in s:
    s = s.replace(old_keys, new_keys, 1)
elif new_keys not in s:
    raise SystemExit("missing keyboard bytearray-membership anchor")

if s.count("self.device.send_report(self.report, 1)") != 1:
    raise SystemExit("bad keyboard report-id patch count")
if "code in self.report[2:]" in s and "Do not use ``code in self.report[2:]``" not in s:
    raise SystemExit("unsupported bytearray membership remains")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched", p)
