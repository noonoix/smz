#!/usr/bin/env python3
import sys
from pathlib import Path
base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import plan_cycle

class Rng:
    def randint(self, lo, hi): return hi
class Store:
    def clear(self): pass
    def arm(self): pass
class Essentials:
    def __init__(self): self.resume_pending = True; self.calls = []
    def run_resume(self, ctx): self.calls.append("resume"); self.resume_pending = False
    def run_due(self, ctx): self.calls.append("due")
class Ctx:
    plan_api = 3
    screen_w = 1920; screen_h = 1080; speed_min = 0; speed_max = 0
    def __init__(self): self.t = 0; self.resume_essentials = Essentials()
    def now(self): return self.t
    def gate(self): return True
    def sleep_ms(self, ms): self.t += ms / 1000; return True
    def release_all(self): pass

ctx = Ctx()
text = "PLAN|2\nRUNFOR|10,10\nAUTORESUME|1,1,1\nDELAY|1\n"
assert plan_cycle.run_root(text, ctx, Rng(), Store()) == "finished"
assert ctx.resume_essentials.calls[0] == "resume"
assert "due" in ctx.resume_essentials.calls[1:]
assert (base / "CIRCUITPY/plan_cycle.py").read_bytes() == (base / "CIRCUITPY-SPLIT/plan_cycle.py").read_bytes()
print("plan cycle essentials: 5 passed, 0 failed")
