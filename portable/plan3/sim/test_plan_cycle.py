#!/usr/bin/env python3
import random
import sys
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import plan_cycle
from cycle_runtime import ResumeArmStore

ops, policy = plan_cycle.parse_cycle_plan(
    "PLAN|2\nRUNFOR|130,110\nAUTORESUME|1,5,3\nLAUNCH|1,1,3,1,40,20\nDELAY|10\n")
assert policy == {"run": (110, 130), "auto": True, "resume": (3, 5),
                  "launch": (True, 1, (1, 3), (20, 40))}
assert [x[0] for x in ops] == ["PLAN", "DELAY"]

_ops, legacy_policy = plan_cycle.parse_cycle_plan(
    "PLAN|2\nRUNFOR|130,110\nAUTORESUME|1,5,3\nPOSTLAUNCH|1,1,3,1,40,20\nDELAY|10\n")
assert legacy_policy == policy
assert plan_cycle.parse_cycle_plan("PLAN|2\nDELAY|1\n")[1] is None

for bad in (
    "PLAN|2\nRUNFOR|1,2\nDELAY|1\n",
    "PLAN|2\nAUTORESUME|1,3,5\nDELAY|1\n",
    "PLAN|2\nDELAY|1\nRUNFOR|1,2\nAUTORESUME|1,3,5\n",
    "PLAN|2\nRUNFOR|0,2\nAUTORESUME|1,3,5\n",
    "PLAN|2\nRUNFOR|1,2\nAUTORESUME|1,3,5\nLAUNCH|1,0,1,3,20,40\n",
    "PLAN|2\nRUNFOR|1,2\nAUTORESUME|1,3,5\nLAUNCH|1,1,1,3,20,40\nPOSTLAUNCH|1,1,1,3,20,40\n",
    "PLAN|2\nLAUNCH|1,1,1,3,20,40\nDELAY|1\n",
):
    try: plan_cycle.parse_cycle_plan(bad)
    except ValueError: pass
    else: raise AssertionError("bad cycle plan accepted")

class Clock:
    def __init__(self): self.value = 100.0
    def now(self): return self.value

class Ctx:
    plan_api = 3
    screen_w = 1920; screen_h = 1080
    speed_min = 300; speed_max = 2000
    def __init__(self, clock): self.clock = clock; self.events = []
    def now(self): return self.clock.now()
    def gate(self): return True
    def sleep_ms(self, ms): self.clock.value += ms / 1000.0; return True
    def release_all(self): self.events.append("release")
    def restart_windows(self): self.events.append("restart")
    def log(self, msg): self.events.append(msg)

with tempfile.TemporaryDirectory() as td:
    clock = Clock(); ctx = Ctx(clock)
    text = "PLAN|2\nRUNFOR|1,1\nAUTORESUME|1,3,5\nDELAY|1500\n"
    result = plan_cycle.run_root(text, ctx, random.Random(1), ResumeArmStore(str(Path(td) / "arm")))
    assert result == "expired"
    assert ctx.events == ["cycle: Launch Steps missing - skipped", "release", "restart"]
    assert (Path(td) / "arm").read_text() == "AUTO_RESUME_ARMED"

def parity_bytes(path):
    return path.read_bytes().replace(b"  # Main runtime starts after Launch/Resume preparation.", b"")

assert parity_bytes(base / "CIRCUITPY/plan_cycle.py") == parity_bytes(base / "CIRCUITPY-SPLIT/plan_cycle.py")
assert (base / "CIRCUITPY/cycle_runtime.py").read_bytes() == (base / "CIRCUITPY-SPLIT/cycle_runtime.py").read_bytes()
print("plan cycle adapter: 20 passed, 0 failed")
