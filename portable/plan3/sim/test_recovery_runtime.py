#!/usr/bin/env python3
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import recovery_runtime

source = "PLAN|2\nKEY|combo=13\n"
out = recovery_runtime.wrap(source, (1200, 1300, 500, 900, 0), "main_recovery.txt")
assert out.startswith("PLAN|2\n")
assert out.count("KEY|combo=13") == 5
assert ["DELAY|5000", "DELAY|10000", "DELAY|20000", "DELAY|40000", "DELAY|80000"] == [
    line for line in out.splitlines() if line.startswith("DELAY|")]
assert out.count("IFLUX|1200,1300,500,900,0") == 5
assert "BEEP|" not in out
assert "final failure: no-crash continuation" in out
assert "GOTO|__MAIN_DC_RECOVERY_OK" in out
assert recovery_runtime.wrap(source, None, "ordinary.txt") == source
try:
    recovery_runtime.wrap(source, None, "launch_recovery.txt")
except ValueError as exc:
    assert "Wait For Light If" in str(exc)
else:
    raise AssertionError("recovery call outside light If was accepted")
assert (base / "CIRCUITPY/recovery_runtime.py").read_bytes() == (base / "CIRCUITPY-SPLIT/recovery_runtime.py").read_bytes()
print("bounded DC recovery runtime: 10 passed, 0 failed")
