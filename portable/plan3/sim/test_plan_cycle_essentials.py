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
    def __init__(self): self.t = 0; self.resume_essentials = Essentials(); self.events = []
    def now(self): return self.t
    def gate(self): return True
    def sleep_ms(self, ms): self.t += ms / 1000; return True
    def release_all(self): self.events.append("release")
    def kdown(self, vk): self.events.append(("down", vk))
    def kup(self, vk): self.events.append(("up", vk))
    def log(self, msg): self.events.append(msg)

ctx = Ctx()
text = "PLAN|2\nRUNFOR|10,10\nAUTORESUME|1,1,1\nPOSTLAUNCH|1,1,1,1,2,2\nDELAY|1\n"
assert plan_cycle.run_root(text, ctx, Rng(), Store()) == "finished"
assert ctx.events.index(("down", 91)) < ctx.events.index(("down", 49))
assert ctx.events.index(("up", 49)) < ctx.events.index(("up", 91))
assert ctx.resume_essentials.calls[0] == "resume"
assert "due" in ctx.resume_essentials.calls[1:]

def parity_bytes(path):
    return path.read_bytes().replace(b"  # Main runtime starts after Launch/Resume preparation.", b"")
assert parity_bytes(base / "CIRCUITPY/plan_cycle.py") == parity_bytes(base / "CIRCUITPY-SPLIT/plan_cycle.py")
print("plan cycle essentials + shared Launch: 8 passed, 0 failed")
