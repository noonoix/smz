#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
if p.name == "live_light_guard.py":
    old = '    "Desktop": "desktop_steps.txt",\n    "LoginOrDc": "login_or_dc_steps.txt",'
    new = '    "Desktop": "desktop_steps.txt",\n    "Restart": "restart_steps.txt",\n    "LoginOrDc": "login_or_dc_steps.txt",'
else:
    old = '_VALID_ROUTE_NAMES = ("desktop_steps.txt", "login_or_dc_steps.txt",'
    new = '_VALID_ROUTE_NAMES = ("desktop_steps.txt", "restart_steps.txt", "login_or_dc_steps.txt",'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("missing Restart route anchor in " + str(p))
if s.count("restart_steps.txt") < 1:
    raise SystemExit("Restart route patch failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched", p)
