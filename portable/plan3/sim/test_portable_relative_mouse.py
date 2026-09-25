#!/usr/bin/env python3
"""Hostless mouse contract for the modern Pico + ARM 2.8 runtime."""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
MODERN = ROOT / "CIRCUITPY-MODERN"
sys.path.insert(0, str(MODERN))
for name in ("plan_engine", "plan_engine_parse", "plan_engine_human", "plan_engine_exec"):
    sys.modules.pop(name, None)
import plan_engine


class RelativeCtx:
    plan_api = 3
    mouse_mode = "relative"
    screen_w = 1920
    screen_h = 1080
    speed_min = 0
    speed_max = 2000

    def __init__(self):
        self.rel = []
        self.logs = []
        self.t = 0

    def now(self): return self.t
    def gate(self): return True
    def sleep_ms(self, ms): self.t += ms / 1000.0; return True
    def setres(self, w, h): self.screen_w, self.screen_h = w, h
    def get_mouse_pos(self): raise AssertionError("relative RMOUSE queried host cursor")
    def set_mouse_pos(self, x, y): raise AssertionError("relative RMOUSE persisted fake absolute cursor")
    def mmove(self, x, y): raise AssertionError("relative RMOUSE sent absolute MMOVE")
    def mmove_relative(self, dx, dy): self.rel.append((int(dx), int(dy)))
    def log(self, text): self.logs.append(text)


text = "\n".join((
    "PLAN|2",
    "SCREEN|1920,1080",
    "SPEED|300,2000",
    "RMOUSE|region=1301,0,378,1049|before=0,0|after=0,0|curve=15,45|mid=0:0,0|over=0|idle=5,12:0,0",
))
ctx = RelativeCtx()
random.seed(2801)
plan_engine.run_plan(plan_engine.parse_plan(text), ctx)
assert ctx.rel, "relative path emitted no reports"
dx = sum(point[0] for point in ctx.rel)
dy = sum(point[1] for point in ctx.rel)
assert 126 <= abs(dx) <= 377, (dx, dy)
assert 90 <= abs(dy) <= 270, (dx, dy)
assert all(abs(x) <= 127 and abs(y) <= 127 for x, y in ctx.rel), ctx.rel
assert any("rmouse-rel" in line for line in ctx.logs), ctx.logs
print("PASS portable RMOUSE uses native relative deltas", len(ctx.rel), dx, dy)

# Absolute MOVETO must fail instead of silently pretending the virtual centre is
# the real Windows cursor. This protects fully portable runs from cursor jumps.
try:
    plan_engine.run_plan(plan_engine.parse_plan("PLAN|2\nMOVETO|x=100|y=200"), RelativeCtx())
except ValueError as exc:
    assert "absolute cursor origin" in str(exc)
else:
    raise AssertionError("portable MOVETO did not fail closed")
print("PASS portable MOVETO fails closed")

arm_dir = ROOT.parents[1] / "firmware" / "arm28"
source = (arm_dir / "ams_board28.ino").read_text(encoding="utf-8")
impl = (arm_dir / "ams_board26_impl.h").read_text(encoding="utf-8")
assert "BootMouse.begin();" in impl
assert "BootMouse.move(sx, sy, 0);" in impl
assert 'if (!strcmp(mode, "rel"))' in impl
rel_branch = impl.split('if (!strcmp(mode, "rel"))', 1)[1].split("else if", 1)[0]
assert "mouse_move_relative_native(x, y)" in rel_branch
assert "mouse_move_abs" not in rel_branch
assert "|REL=1" in source
print("PASS ARM 2.8 rel-MMOVE uses native relative HID")
