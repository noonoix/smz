#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

old_init = "        self.report = bytearray(8)\n"
new_init = """        self.report = bytearray(8)
        # Clear any key state the host may retain across a firmware reload.
        try:
            self._send()
        except Exception:
            pass
"""
if old_init in s:
    s = s.replace(old_init, new_init, 1)
elif new_init not in s:
    raise SystemExit("missing keyboard report initialization anchor")

old_release = """    def release_all(self):
        for index in range(8):
            self.report[index] = 0
        self._send()
"""
new_release = """    def release_all(self):
        for index in range(8):
            self.report[index] = 0
        # Repeat the zero report. This is deliberately fail-safe: a cleanup
        # failure must not abort the route before the host sees key-up.
        for _ in range(2):
            try:
                self._send()
            except Exception:
                pass
"""
if old_release in s:
    s = s.replace(old_release, new_release, 1)
elif new_release not in s:
    raise SystemExit("missing release_all anchor")

p.write_text(s, encoding="utf-8", newline="\n")
print("patched HID release safety:", p)
