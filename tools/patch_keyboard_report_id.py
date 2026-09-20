#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = '''    def _send(self):
        self.device.send_report(self.report)
'''
new = '''    def _send(self):
        try:
            # CircuitPython's standard keyboard descriptor uses report ID 1.
            self.device.send_report(self.report, 1)
        except TypeError:
            # Compatibility with older one-argument Device.send_report builds.
            self.device.send_report(self.report)
'''
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("missing keyboard send-report anchor")
if s.count("self.device.send_report(self.report, 1)") != 1:
    raise SystemExit("bad keyboard report-id patch count")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched", p)
