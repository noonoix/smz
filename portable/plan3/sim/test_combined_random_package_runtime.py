#!/usr/bin/env python3
"""Low-memory Combined Guard Random Package contract."""
import io
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "CIRCUITPY"))
from random_package_runtime import run_file_package  # noqa: E402

class Owner:
    def __init__(self): self.events = []
    def emit(self, value): self.events.append(("log", value))

def action(owner, op, args, expected):
    owner.events.append((op, args))
    return True

def run(args, body, seed):
    owner = Owner(); stream = io.StringIO(body + "TAIL|ok\n")
    random.seed(seed)
    assert run_file_package(stream, args, owner, None, action)
    assert stream.readline().strip() == "TAIL|ok"
    return [event for event in owner.events if event[0] != "log"]

body = """KEY|combo=49
DELAY|88,188
PKGITEM
KEY|combo=50
DELAY|122,222
PKGITEM
KEY|combo=51
DELAY|111,444
ENDPKG
"""
all_events = run("all,1,3", body, 7)
assert sorted(int(args.split("=")[1]) for op, args in all_events if op == "KEY") == [49, 50, 51]
for seed in range(12):
    events = run("pick,1,2", body, seed)
    keys = [args for op, args in events if op == "KEY"]
    assert 1 <= len(keys) <= 2 and len(keys) == len(set(keys))

nested = """RPKG|all,1,2
KEY|combo=65
PKGITEM
KEY|combo=66
ENDPKG
PKGITEM
KEY|combo=67
ENDPKG
"""
assert sorted(int(args.split("=")[1]) for op, args in run("all,1,2", nested, 3) if op == "KEY") == [65, 66, 67]
print("combined low-memory Random Package contract: passed")
