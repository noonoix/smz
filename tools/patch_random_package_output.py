#!/usr/bin/env python3
"""Add low-memory Random Package support to the built Combined Guard runtime."""
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

helpers = '''def _light_package_delay(owner, args, expected):
    parts = args.split(",")
    if len(parts) not in (1, 2): raise ValueError("bad DELAY range")
    lo = int(parts[0]); hi = int(parts[-1])
    if lo < 0 or hi < 0: raise ValueError("negative DELAY")
    if hi < lo: lo, hi = hi, lo
    value = lo if hi <= lo else _light_random.randint(lo, hi)
    return _light_sleep(owner, value, expected)


def _light_package_action(owner, op, args, expected):
    if op == "DELAY": return _light_package_delay(owner, args, expected)
    if op == "KEY": return _light_key(owner, args, expected)
    if op == "TYPE": return _light_type(owner, args, expected)
    if op in ("RMOUSE", "MOVETO"): return _light_mouse(owner, op, args, expected)
    if op in ("KDOWN", "KUP"):
        code = _light_keycode(int(args))
        if op == "KDOWN": owner.keyboard.press(code)
        else: owner.keyboard.release(code)
        owner.emit("EVT|DEBUG|STEP/%s vk=%s" % (op, args))
        return _light_gate(owner, expected)
    if op == "BEEP":
        fields = args.split(",")
        if len(fields) != 2: raise ValueError("bad BEEP")
        owner.emit("EVT|DEBUG|STEP/BEEP %s,%s" % (fields[0], fields[1]))
        return _light_beep(owner, int(fields[0]), int(float(fields[1])), expected)
    raise ValueError("unsupported package command: " + op)


'''

if "def _light_package_action(owner, op, args, expected):" not in s:
    anchor = "def _run_light_route(owner, name):\n"
    if anchor not in s:
        raise SystemExit("missing Combined Guard route anchor")
    s = s.replace(anchor, helpers + anchor, 1)

old = '''            elif op == "DELAY":
                a = args.split(",")
                if not _light_sleep(owner, int(a[0]), expected): return False
            elif op == "BEEP":'''
new = '''            elif op == "DELAY":
                if not _light_package_delay(owner, args, expected): return False
            elif op == "RPKG":
                from random_package_runtime import run_file_package
                if not run_file_package(fh, args, owner, expected, _light_package_action): return False
            elif op == "BEEP":'''
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("missing Combined Guard DELAY dispatch anchor")

required = (
    "def _light_package_delay(owner, args, expected):",
    "def _light_package_action(owner, op, args, expected):",
    'elif op == "RPKG":',
    "from random_package_runtime import run_file_package",
)
missing = [token for token in required if token not in s]
if missing:
    raise SystemExit("Random Package output contract missing: " + ", ".join(missing))
p.write_text(s, encoding="utf-8", newline="\n")
print("patched low-memory Random Package support:", p)
