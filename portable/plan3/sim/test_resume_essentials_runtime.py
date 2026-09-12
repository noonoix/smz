#!/usr/bin/env python3
import random
import sys
from pathlib import Path
base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import resume_essentials_runtime as rer

text = """ESSENTIALS|1
ITEM|vk=55|interval=3420,3780|hold=45,105|before=120,380|after=700,1600|priority=20|resume=1
ITEM|vk=54|interval=1680,1920|hold=45,105|before=120,380|after=700,1600|priority=10|resume=1
ITEM|vk=53|interval=270,330|hold=45,105|before=120,380|after=700,1600|priority=30|resume=1
"""
items = rer.parse(text)
assert [x["vk"] for x in items] == [55, 54, 53]
clock = [1000.0]
events = []
class Ctx:
    def sleep_ms(self, ms): events.append(("sleep", ms)); clock[0] += ms / 1000; return True
    def kdown(self, vk): events.append(("down", vk))
    def kup(self, vk): events.append(("up", vk))
ctx = Ctx()
mgr = rer.Manager(items, now=lambda: clock[0], rng=random.Random(42), resume_pending=True)
assert mgr.run_resume(ctx) == 3
assert mgr.resume_pending is False and mgr.initialized
assert sorted(x["vk"] for x in items if x["next"] is not None) == [53, 54, 55]
for vk in (53, 54, 55):
    assert ("down", vk) in events and ("up", vk) in events

# Priority order at a safe boundary: potion(10), food(20), tea(30).
events.clear()
for item in items: item["next"] = clock[0]
assert mgr.run_due(ctx) == 3
assert [value for kind, value in events if kind == "down"] == [54, 55, 53]

# No interruption before a safe-boundary call.
events.clear()
for item in items: item["next"] = clock[0] - 1
clock[0] += 50
assert events == []
assert mgr.run_due(ctx) == 3

# Key-up is guaranteed when a hold is aborted.
class AbortCtx(Ctx):
    calls = 0
    def sleep_ms(self, ms):
        self.calls += 1
        return self.calls < 2
abort_events = events
events.clear()
try:
    rer.Manager(rer.parse(text)[:1], now=lambda: 0, rng=random.Random(1), resume_pending=True).run_resume(AbortCtx())
except rer.EssentialAbort:
    pass
else:
    raise AssertionError("aborted hold was accepted")
assert events[-1] == ("up", 55)
assert (base / "CIRCUITPY/resume_essentials_runtime.py").read_bytes() == (base / "CIRCUITPY-SPLIT/resume_essentials_runtime.py").read_bytes()

# The app-selected Random Package is exported as a standalone PLAN|2 pre-pass.
import tempfile
from pathlib import Path as _Path
plan_events = []
class PlanCtx:
    screen_w = 1920; screen_h = 1080; speed_min = 0; speed_max = 0
    def now(self): return 0
    def gate(self): return True
    def sleep_ms(self, ms): plan_events.append(("sleep", ms)); return True
plan_file = _Path(tempfile.gettempdir()) / "resume-essentials-plan2-test.txt"
plan_file.write_text("PLAN|2\nDELAY|7\n", encoding="utf-8")
try:
    plan_mgr = rer.Manager.from_file(str(plan_file), resume_pending=True)
    assert isinstance(plan_mgr, rer.PlanManager)
    assert plan_mgr.run_resume(PlanCtx()) == 1
    assert plan_mgr.resume_pending is False and plan_mgr.initialized
    assert plan_mgr.run_due(PlanCtx()) == 0
    assert plan_events == [("sleep", 7)]
finally:
    plan_file.unlink(missing_ok=True)

print("resume essentials runtime: 35 passed, 0 failed")
