#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioural tests for tools/plan_gen.py (the .amsj -> plan.txt compiler).

Golden tests: the generator is deterministic (randomness lives in the engine at
run time), so the emitted plan is compared BYTE-EXACT against the frozen files
in examples/*.plan.txt. Negative tests prove the hard rule: no unsupported step
is ever silently skipped - the build blocks and names every offending step.
End-to-end: the generated reference plan is also EXECUTED on a fake ctx.
"""
import json
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _cand in (_HERE, _ROOT, os.path.join(_ROOT, "CIRCUITPY"), os.path.join(_ROOT, "tools"), os.getcwd()):
    if os.path.exists(os.path.join(_cand, "plan_engine.py")):
        sys.path.insert(0, _cand)
for _cand in (os.path.join(_ROOT, "tools"), _HERE, os.getcwd()):
    if os.path.exists(os.path.join(_cand, "winr.py")):
        sys.path.insert(0, _cand)
        break
import plan_engine as pe                     # noqa: E402
import plan_gen as pg                        # noqa: E402

PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS", name)
    else:
        FAIL += 1
        print("FAIL", name)


EXAMPLES = os.path.join(_ROOT, "examples")


def cli(argv):
    return pg.main(argv)


def build_opts(**over):
    settings = {"PlayRepeatMode": "once", "PlayRepeatTimes": 10, "PlayRepeatValue": 1,
                "PlayRepeatUnit": "minute", "MouseMoveSpeedMin": 300, "MouseMoveSpeedMax": 2000,
                "TypeKeyMinMs": 80, "TypeKeyMaxMs": 220, "KeyboardBoard": "pico"}
    settings.update(over.pop("settings", {}))
    opts = {"screen_w": 1920, "screen_h": 1080, "settings": settings,
            "type_key_min": 80, "type_key_max": 220, "out_name": "plan.txt"}
    opts.update(over)
    return opts


# -- 1. golden: ref-mouse-keys --------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    rc = cli([os.path.join(EXAMPLES, "ref-mouse-keys.amsj"), "-o", "out.txt", "--out-dir", td])
    got = open(os.path.join(td, "out.txt"), encoding="utf-8").read()
    golden = open(os.path.join(EXAMPLES, "ref-mouse-keys.plan.txt"), encoding="utf-8").read()
    check("golden ref-mouse-keys compiles (rc=0)", rc == 0)
    check("golden ref-mouse-keys is byte-exact", got == golden)
    check("golden ref-mouse-keys parses with the real engine", bool(pe.parse_plan(got)))

# -- 2. golden: ref-flow --------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    rc = cli([os.path.join(EXAMPLES, "ref-flow.amsj"), "-o", "out.txt", "--out-dir", td])
    got = open(os.path.join(td, "out.txt"), encoding="utf-8").read()
    golden = open(os.path.join(EXAMPLES, "ref-flow.plan.txt"), encoding="utf-8").read()
    check("golden ref-flow compiles (rc=0)", rc == 0)
    check("golden ref-flow is byte-exact", got == golden)
    check("golden ref-flow parses with the real engine", bool(pe.parse_plan(got)))

# -- 3. blocking paths ----------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    rc = cli([os.path.join(EXAMPLES, "err-pgroup.amsj"), "--out-dir", td])
    check("pgroup with a loop blocks (rc=1)", rc == 1)
    check("blocked build writes NO plan file", not os.path.exists(os.path.join(td, "plan.txt")))

with tempfile.TemporaryDirectory() as td:
    rc = cli([os.path.join(EXAMPLES, "daroon1.amsj"), "--out-dir", td])
    check("daroon1 blocks on findImage (rc=1)", rc == 1)
    check("daroon1 blocked => nothing written", not os.path.exists(os.path.join(td, "plan.txt")))

try:
    pg.build(os.path.join(EXAMPLES, "daroon1.amsj"), build_opts())
    check("daroon1 raises _Blocked", False)
except pg._Blocked as b:
    joined = "\n".join(b.errors)
    check("daroon1 names all 8 findImage steps",
          joined.count("findImage needs machine vision") == 8)
    check("daroon1 reports the missing End If of 13.6", "End If" in joined and "13.6" in joined)


def blocked_with(doc):
    """Compile an in-memory doc; return the error list."""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "bad.amsj")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        try:
            pg.build(p, build_opts())
            return None
        except pg._Blocked as b:
            return b.errors


def step(t, props=None, **kw):
    d = {"Type": t, "Name": "", "Delay": 0, "IsDisabled": False,
         "Props": props or {}, "Children": []}
    d.update(kw)
    return d


def doc(steps):
    return {"app": "AMS", "version": "0.8.2", "steps": steps}


errs = blocked_with(doc([step("typeText", {"text": "x", "mode": "clipboard"})]))
check("clipboard typing blocks", errs and "clipboard" in errs[0])
errs = blocked_with(doc([step("typeText", {"text": "x", "secret": True})]))
check("secret typing blocks", errs and "clipboard" in errs[0])
errs = blocked_with(doc([step("typeText", {"text": "سلام"})]))
check("non-ASCII text blocks with advice", errs and "ASCII" in errs[0])
errs = blocked_with(doc([step("label", {"label": "a"}), step("label", {"label": "a"})]))
check("duplicate label blocks", errs and "duplicate label" in errs[0])
errs = blocked_with(doc([step("comment", {"text": "End If"})]))
check("orphan End If blocks", errs and "no matching block head" in errs[0])
errs = blocked_with(doc([step("gotoLabel", {"label": "ghost"})]))
# GOTO to a missing label is caught by the engine's own parser (dogfood gate)
check("goto to a missing label blocks", errs is not None and len(errs) >= 1)
errs = blocked_with(doc([step("playScript", {"path": "C:\\no\\such\\file.amsj"})]))
check("missing playScript child blocks", errs and "not found" in errs[0])

# -- 4. playScript include: child compiles, INCLUDE line emitted ----------------
with tempfile.TemporaryDirectory() as td:
    child = doc([step("delay", {"minMs": 5, "maxMs": 5})])
    cpath = os.path.join(td, "child-plan.amsj")
    with open(cpath, "w", encoding="utf-8") as fh:
        json.dump(child, fh)
    parent = doc([step("playScript", {"path": cpath})])
    ppath = os.path.join(td, "parent.amsj")
    with open(ppath, "w", encoding="utf-8") as fh:
        json.dump(parent, fh)
    rc = cli([ppath, "--out-dir", td])
    ptxt = open(os.path.join(td, "plan.txt"), encoding="utf-8").read()
    check("playScript compiles (rc=0)", rc == 0)
    check("parent plan has INCLUDE|file=child-plan.txt", "INCLUDE|file=child-plan.txt" in ptxt)
    check("child plan file written next to it", os.path.exists(os.path.join(td, "child-plan.txt")))
    if os.path.exists(os.path.join(td, "child-plan.txt")):
        ctxt_ = open(os.path.join(td, "child-plan.txt"), encoding="utf-8").read()
        check("child plan parses", bool(pe.parse_plan(ctxt_)))
        check("child plan carries the step", "DELAY|5" in ctxt_)

# include cycle: a includes b, b includes a -> blocked
with tempfile.TemporaryDirectory() as td:
    pa = os.path.join(td, "a.amsj")
    pb = os.path.join(td, "b.amsj")
    with open(pa, "w", encoding="utf-8") as fh:
        json.dump(doc([step("playScript", {"path": pb})]), fh)
    with open(pb, "w", encoding="utf-8") as fh:
        json.dump(doc([step("playScript", {"path": pa})]), fh)
    try:
        pg.build(pa, build_opts())
        check("include cycle blocks", False)
    except pg._Blocked as b:
        check("include cycle blocks", any("cycle" in e for e in b.errors))

# -- 5. Play Options wrapper from ams-settings.json ----------------------------
def settings_file(td, **kw):
    p = os.path.join(td, "ams-settings.json")
    base = {"PlayRepeatMode": "once", "PlayRepeatTimes": 10, "PlayRepeatValue": 1,
            "PlayRepeatUnit": "minute", "MouseMoveSpeedMin": 300, "MouseMoveSpeedMax": 2000}
    base.update(kw)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(base, fh)
    return p


with tempfile.TemporaryDirectory() as td:
    src = os.path.join(EXAMPLES, "ref-mouse-keys.amsj")
    s = settings_file(td, PlayRepeatMode="times", PlayRepeatTimes=3)
    rc = cli([src, "-o", "o.txt", "--out-dir", td, "--settings", s])
    txt = open(os.path.join(td, "o.txt"), encoding="utf-8").read()
    check("times=3 wraps the whole plan in LOOP|3", rc == 0 and "\nLOOP|3\n" in txt
          and txt.rstrip().endswith("ENDLOOP"))
with tempfile.TemporaryDirectory() as td:
    src = os.path.join(EXAMPLES, "ref-mouse-keys.amsj")
    s = settings_file(td, PlayRepeatMode="timed", PlayRepeatValue=2, PlayRepeatUnit="minute")
    rc = cli([src, "-o", "o.txt", "--out-dir", td, "--settings", s])
    txt = open(os.path.join(td, "o.txt"), encoding="utf-8").read()
    check("timed 2 minutes wraps in LOOPTIME|120", rc == 0 and "\nLOOPTIME|120\n" in txt)
with tempfile.TemporaryDirectory() as td:
    src = os.path.join(EXAMPLES, "ref-mouse-keys.amsj")
    s = settings_file(td)   # once
    rc = cli([src, "-o", "o.txt", "--out-dir", td, "--settings", s])
    txt = open(os.path.join(td, "o.txt"), encoding="utf-8").read()
    # the fixture itself contains a forLoop count=3 (one LOOP|3); a Play-Options
    # wrapper would add a SECOND one at the top plus a trailing ENDLOOP.
    check("once = no wrapper", rc == 0 and txt.count("\nLOOP|") == 1
          and "LOOPTIME|" not in txt and not txt.rstrip().endswith("ENDLOOP"))

# speed range + migration come from settings
with tempfile.TemporaryDirectory() as td:
    s = settings_file(td, MouseMoveSpeedMin=0, MouseMoveSpeedMax=2300)   # factory-pair migrates
    rc = cli([os.path.join(EXAMPLES, "ref-mouse-keys.amsj"), "-o", "o.txt", "--out-dir", td,
              "--settings", s])
    txt = open(os.path.join(td, "o.txt"), encoding="utf-8").read()
    check("0/2300 migrates to 300/2000 (app rule)", "SPEED|300,2000" in txt)

# -- 6. disabled steps are counted, never emitted -------------------------------
try:
    files, gen, _c = pg.build(os.path.join(EXAMPLES, "ref-mouse-keys.amsj"), build_opts())
    txt = files["plan.txt"]
    check("disabled step counted", len(gen.disabled) == 1 and "disabled probe" in gen.disabled[0])
    check("disabled step emits nothing (no KDOWN|81 anywhere)", "KDOWN|81" not in txt and "combo=81" not in txt)
except pg._Blocked:
    check("disabled-count build works", False)

# -- 7. end-to-end: the generated reference plan RUNS on a fake ctx -------------
class Ctx:
    plan_api = 3
    screen_w, screen_h = 1920, 1080
    speed_min, speed_max = 300, 2000

    def __init__(self):
        self.ev = []
        self._t = 0.0

    def now(self):
        return self._t

    def sleep_ms(self, ms):
        self._t += ms / 1000.0
        return True

    def log(self, m):
        pass

    def mmove(self, x, y):
        self.ev.append(("mm", x, y))

    def mclick(self, b, n, hmin, hmax):
        self.ev.append(("click", b, n))

    def ktext(self, hmin, hmax, text):
        self.ev.append(("ktext", text))

    def kcombo(self, vk):
        self.ev.append(("kcombo", vk))

    def key(self, vk, hold):
        self.ev.append(("key", vk))

    def key_combo(self, vks, hmin, hmax):
        self.ev.append(("keyc", tuple(vks)))

    def kdown(self, vk):
        self.ev.append(("down", vk))

    def kup(self, vk):
        self.ev.append(("up", vk))

    def wheel(self, d):
        self.ev.append(("wheel", d))

    def raw(self, line):
        self.ev.append(("raw", line))
        return "OK"

    def wait_light(self, lo, hi, stable, to, mode):
        return False

    def wait_sound(self, thr, mn, to):
        return False

    def trg_sound(self, *a):
        return False

    def setres(self, w, h):
        self.ev.append(("setres", w, h))

    def read_plan_file(self, name):
        raise OSError(name)

    def beep(self, f, ms):
        self.ev.append(("beep", f, ms))


files, _g, _c = pg.build(os.path.join(EXAMPLES, "ref-mouse-keys.amsj"), build_opts())
ops = pe.parse_plan(files["plan.txt"])
ctx = Ctx()
pe.run_plan(ops, ctx)

def ev_count(kind, val=None):
    return sum(1 for e in ctx.ev if e[0] == kind and (val is None or e[1] == val))

check("e2e: SETRES fired once with the screen", ctx.ev.count(("setres", 1920, 1080)) == 1)
check("e2e: forLoop ran its keystroke exactly 3 times", ev_count("keyc", (70,)) == 3)
check("e2e: Ctrl+E combo fired once", ev_count("keyc", (162, 69)) == 1)
check("e2e: KDOWN/KUP of SHIFT fired once each", ev_count("down", 160) == 1 and ev_count("up", 160) == 1)
check("e2e: text typed", ev_count("ktext") >= 1)
check("e2e: one click landed", ev_count("click", "left") == 1)
check("e2e: RAW PING reached the board", ev_count("raw", "PING") == 1)
check("e2e: human move walked the mouse", ev_count("mm") > 0)
check("e2e: wheel scrolled", ev_count("wheel", -3) == 1)

print("=== Results: %d passed, %d failed ===" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
