#!/usr/bin/env python3
"""Differential parity tests for the generated three-file PLAN|2 runtime."""
from pathlib import Path
import importlib.util
import random
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
CAN = ROOT / "CIRCUITPY" / "plan_engine.py"
SPLIT = ROOT / "CIRCUITPY-SPLIT"

def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

canonical = load_file("canonical_pe", CAN)
sys.path.insert(0, str(SPLIT))
for name in ("plan_engine", "plan_motion", "plan_typing"):
    sys.modules.pop(name, None)
split = __import__("plan_engine")

class Ctx:
    plan_api = 3; screen_w = 1920; screen_h = 1080; speed_min = 0; speed_max = 2000
    def __init__(self, files=None, snd=None, lux=None):
        self.files = files or {}; self.snd = list(snd or []); self.lux = list(lux or [])
        self.ev = []; self.pos = None; self.t = 0
    def gate(self): self.ev.append(("gate",)); return True
    def beep(self, f, m): self.ev.append(("beep", f, m))
    def now(self): return self.t
    def sleep_ms(self, m): self.t += m / 1000; self.ev.append(("delay", m)); return True
    def get_mouse_pos(self): return self.pos
    def set_mouse_pos(self, x, y): self.pos = (int(x), int(y)); self.ev.append(("pos", int(x), int(y)))
    def mmove(self, x, y): self.ev.append(("move", int(x), int(y)))
    def mclick(self, *a): self.ev.append(("click",) + a)
    def ktext(self, *a): self.ev.append(("text",) + a)
    def kcombo(self, *a): self.ev.append(("combo1",) + a)
    def wait_light(self, *a): self.ev.append(("lux",) + a); return self.lux.pop(0) if self.lux else False
    def key(self, *a): self.ev.append(("key",) + a)
    def log(self, *a): self.ev.append(("log",) + a)
    def wait_sound(self, *a): self.ev.append(("sound",) + a); return self.snd.pop(0) if self.snd else False
    def trg_sound(self, *a): self.ev.append(("trgsnd",) + a); return True
    def key_combo(self, *a): self.ev.append(("keycombo",) + tuple(tuple(x) if isinstance(x, list) else x for x in a))
    def kdown(self, *a): self.ev.append(("down",) + a)
    def kup(self, *a): self.ev.append(("up",) + a)
    def wheel(self, *a): self.ev.append(("wheel",) + a)
    def raw(self, *a): self.ev.append(("raw",) + a); return "OK|RAW"
    def read_plan_file(self, n): return self.files[n]
    def setres(self, *a): self.ev.append(("setres",) + a)

PLANS = [
    "PLAN|1\nSCREEN|1920,1080\nSPEED|300,2000\nTYPE|h=80,220|text=Hello%7CWorld\nDELAY|5,9\nCLICK|btn=left|n=2|hold=10,20",
    "PLAN|2\nIFSND|60,100,1000\nKEY|combo=17+65|hold=30,40\nELSE\nWHEEL|-2\nENDIF\nKDOWN|16\nKUP|16\nRAW|MCLICK|left",
    "PLAN|2\nWSND|50,80,500\nIFLUX|10,20,100,500,1\nKDOWN|65\nELSE\nKUP|65\nENDIF",
    "PLAN|2\nTRGSND|60,100,30000,1,80,180,30,90\nMOVETO|x=321|y=654|human=0",
    "PLAN|2\nLOOP|3\nDELAY|100\nENDLOOP\nLOOPTIME|0.25\nDELAY|100\nENDLOOP",
    "PLAN|2\nRPKG|seq,0,2\nDELAY|5\nPKGITEM\nBEEP|880,12\nENDPKG",
    "PLAN|2\nPGROUP\nKDOWN|17\nKUP|17\nPARITEM\nWHEEL|3\nWHEEL|-3\nENDPAR",
    "PLAN|2\nSCREEN|1920,1080\nSPEED|300,2000\nRMOUSE|region=100,120,1506,623|before=120,450|after=150,600|curve=15,45|mid=12:100,500|over=25|idle=5,12:800,3000",
]
files = {"child.txt": "PLAN|2\nTYPE|h=10,20|text=child\nINCLUDE|file=child.txt"}
PLANS.append("PLAN|2\nINCLUDE|file=child.txt\nTYPE|h=1,2|text=root")

passed = failed = 0
for i, text in enumerate(PLANS, 1):
    try:
        a = canonical.parse_plan(text); b = split.parse_plan(text)
        assert repr(a) == repr(b), (a, b)
        kwargs = {"files": files}
        if "IFSND" in text: kwargs["snd"] = [True]
        if "IFLUX" in text: kwargs["lux"] = [False]
        ca = Ctx(**kwargs); cb = Ctx(**kwargs)
        random.seed(100 + i); canonical.run_plan(a, ca)
        random.seed(100 + i); split.run_plan(b, cb)
        assert ca.ev == cb.ev and ca.pos == cb.pos and abs(ca.t - cb.t) < 1e-9
        print("PASS parity", i, "events", len(ca.ev)); passed += 1
    except Exception:
        failed += 1; print("FAIL parity", i); traceback.print_exc()

NEG = [
    ("PLAN|2\nELSE", "ELSE outside"), ("PLAN|2\nENDIF", "without IFSND"),
    ("PLAN|2\nGOTO|missing", "no matching LABEL"), ("PLAN|2\nINCLUDE|file=../x.txt", "plain *.txt"),
    ("PLAN|2\nRPKG|pick,0,5\nDELAY|1\nENDPKG", "out of range"),
    ("PLAN|2\nPGROUP\nWHEEL|1\nENDPAR", "at least two branches"),
]
for i, (text, needle) in enumerate(NEG, 1):
    try:
        ea = eb = None
        try: canonical.parse_plan(text)
        except Exception as exc: ea = str(exc)
        try: split.parse_plan(text)
        except Exception as exc: eb = str(exc)
        assert ea == eb and needle in ea, (ea, eb)
        print("PASS negative", i, ea); passed += 1
    except Exception:
        failed += 1; print("FAIL negative", i); traceback.print_exc()

# PLAN2_H5_CONTROL_FIX: aborting inside lazy motion must use the core exception.
class AbortMotionCtx(Ctx):
    def sleep_ms(self, m):
        self.ev.append(("delay", m))
        return False

abort_text = "PLAN|2\nSCREEN|1920,1080\nRMOUSE|region=100,120,200,150|before=1,1|after=0,0|curve=15,45|mid=0:0,0|over=0|idle=1,1:0,0"
for engine, name in ((canonical, "canonical"), (split, "split")):
    caught = False
    try:
        engine.run_plan(engine.parse_plan(abort_text), AbortMotionCtx())
    except engine.PlanAbort:
        caught = True
    assert caught, name + " did not raise its exported PlanAbort"
print("PASS h5 lazy-motion PlanAbort parity"); passed += 1

bundle = {
    "plan.txt": "PLAN|2\nTYPE|text=PLAN2_OK|h=1,2\nINCLUDE|file=child-a.txt",
    "child-a.txt": "PLAN|2\nRMOUSE|region=100,120,200,150|before=0,0|after=0,0|curve=15,45|mid=0:0,0|over=0|idle=1,1:0,0\nINCLUDE|file=child-b.txt",
    "child-b.txt": "PLAN|2\nCLICK|btn=left|n=1",
}
for engine, name in ((canonical, "canonical"), (split, "split")):
    ctx = Ctx(files=bundle); random.seed(7)
    engine.run_plan(engine.parse_plan(bundle["plan.txt"]), ctx)
    assert any(e[0] == "text" and e[-1] == "PLAN2_OK" for e in ctx.ev)
    assert any(e[0] == "move" for e in ctx.ev)
    print("PASS exact bundle", name, len(ctx.ev)); passed += 1

assert "plan_motion" in sys.modules and "plan_typing" in sys.modules
print("PASS lazy modules loaded on demand"); passed += 1
print("RESULT", passed, "passed", failed, "failed")
raise SystemExit(1 if failed else 0)
