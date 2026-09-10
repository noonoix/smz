#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardware-free behavioural tests for plan_engine v3:
randomPackage (RPKG), parallelGroup (PGROUP), buzzer (BEEP), the keypad gate
(GP3 pause / GP4 stop mid-plan) and the Win+R background launcher macros."""
import random
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _cand in (_HERE, _ROOT, os.path.join(_ROOT, "CIRCUITPY"), os.path.join(_ROOT, "tools"),
              os.path.join(_HERE, "CIRCUITPY"), os.path.join(_HERE, "tools"), os.getcwd()):
    if os.path.exists(os.path.join(_cand, "plan_engine.py")):
        sys.path.insert(0, _cand)
for _cand in (_HERE, _ROOT, os.path.join(_ROOT, "tools"), os.path.join(_HERE, "tools"), os.getcwd()):
    if os.path.exists(os.path.join(_cand, "winr.py")):
        sys.path.insert(0, _cand)

import plan_engine as pe                      # noqa: E402
import winr                                   # noqa: E402

PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("PASS", name)
    else:
        FAIL += 1
        print("FAIL", name)


class Ctx:
    plan_api = 3
    screen_w = 1920
    screen_h = 1080
    speed_min = 0
    speed_max = 2000

    def __init__(self, snd=(), lux=(), files=None, stop_at=0, pause_for=0):
        self.t = 0.0
        self.snd = list(snd)
        self.lux = list(lux)
        self.files = files or {}
        self.ev = []
        self.pos = None
        self.stop_at = stop_at        # gate returns False on this call (GP4 stop)
        self.pause_for = pause_for    # gate blocks this many turns first (GP3 pause)
        self.gates = 0

    # -- keypad ------------------------------------------------------------
    def gate(self):
        self.gates += 1
        if self.pause_for:
            for _ in range(self.pause_for):
                self.ev.append(("paused",))
            self.pause_for = 0
        if self.stop_at and self.gates >= self.stop_at:
            self.ev.append(("stopped",))
            return False
        return True

    def beep(self, freq, ms):
        self.ev.append(("beep", int(freq), int(ms)))

    # -- v1/v2 primitives ---------------------------------------------------
    def now(self):
        return self.t

    def sleep_ms(self, ms):
        self.t += ms / 1000
        self.ev.append(("delay", ms))
        return True

    def get_mouse_pos(self):
        return self.pos

    def set_mouse_pos(self, x, y):
        self.pos = (int(x), int(y))

    def mmove(self, x, y):
        self.ev.append(("move", int(x), int(y)))

    def mclick(self, b, n, a, z):
        self.ev.append(("click", b, n, a, z))

    def ktext(self, a, z, s):
        self.ev.append(("text", a, z, s))

    def kcombo(self, v):
        self.ev.append(("combo1", v))

    def wait_light(self, *a):
        self.ev.append(("lux",) + a)
        return self.lux.pop(0) if self.lux else False

    def key(self, v, h):
        self.ev.append(("key", v, h))

    def log(self, s):
        self.ev.append(("log", s))

    def wait_sound(self, *a):
        self.ev.append(("sound",) + a)
        return self.snd.pop(0) if self.snd else False

    def trg_sound(self, *a):
        self.ev.append(("trgsnd",) + a)
        return True

    def key_combo(self, v, a, z):
        self.ev.append(("keycombo", tuple(v), a, z))

    def kdown(self, v):
        self.ev.append(("down", v))

    def kup(self, v):
        self.ev.append(("up", v))

    def wheel(self, v):
        self.ev.append(("wheel", v))

    def raw(self, s):
        self.ev.append(("raw", s))
        return "OK|RAW"

    def read_plan_file(self, n):
        return self.files[n]

    def setres(self, w, h):
        self.ev.append(("setres", w, h))


class CtxNoBeep(Ctx):
    plan_api = 2
    beep = None


def run(text, seed=7, **kw):
    c = Ctx(**kw)
    random.seed(seed)
    pe.run_plan(pe.parse_plan(text), c)
    return c


def expect_error(name, text, contains):
    try:
        pe.parse_plan(text)
    except Exception as exc:
        check(name, contains in str(exc))
    else:
        check(name, False)


def delays(c):
    return [e[1] for e in c.ev if e[0] == "delay"]


PKG = """PLAN|2
RPKG|%s,%d,%d
DELAY|1
PKGITEM
DELAY|2
PKGITEM
DELAY|3
ENDPKG"""

# -- randomPackage ----------------------------------------------------------
c = run(PKG % ("pick", 1, 1))
d = delays(c)
check("RPKG pick,1,1 runs exactly one item", len(d) == 1 and d[0] in (1, 2, 3))
check("RPKG logs the draw", ("log", "package: 1 of 3") in c.ev)

c = run(PKG % ("seq", 0, 3))
check("RPKG seq keeps file order", delays(c) == [1, 2, 3])

c = run(PKG % ("all", 0, 3))
check("RPKG all runs every item once", sorted(delays(c)) == [1, 2, 3])

fresh = set()
for seed in range(12):
    fresh.add(tuple(delays(run(PKG % ("pick", 2, 2), seed=seed))))
check("RPKG draws a fresh set per pass", len(fresh) > 1)

expect_error("RPKG rejects counts above the item count", PKG % ("pick", 0, 5),
             "out of range")
expect_error("RPKG rejects an unknown mode", PKG % ("shuffle", 1, 2), "unknown RPKG mode")
expect_error("unclosed RPKG is rejected",
             "PLAN|2\nRPKG|pick,1,1\nDELAY|1", "never closed")
expect_error("stray PKGITEM is rejected", "PLAN|2\nPKGITEM\nDELAY|1",
             "outside a package")
expect_error("ENDPAR cannot close a package",
             "PLAN|2\nRPKG|pick,1,1\nDELAY|1\nENDPAR", "closes a RPKG")

c = run("""PLAN|2
LOOP|2
RPKG|seq,0,2
DELAY|5
PKGITEM
DELAY|6
ENDPKG
ENDLOOP""")
check("RPKG nests inside LOOP", delays(c) == [5, 6, 5, 6])

# -- parallelGroup ----------------------------------------------------------
c = run("""PLAN|2
PGROUP
KDOWN|17
KUP|17
PARITEM
WHEEL|3
WHEEL|-3
ENDPAR""")
check("PGROUP interleaves the branches",
      c.ev == [("down", 17), ("wheel", 3), ("up", 17), ("wheel", -3)])

c = run("""PLAN|2
PGROUP
KDOWN|17
PARITEM
WHEEL|1
WHEEL|2
WHEEL|3
ENDPAR""")
check("PGROUP drains the longer branch",
      c.ev == [("down", 17), ("wheel", 1), ("wheel", 2), ("wheel", 3)])

expect_error("PGROUP rejects a loop inside a branch",
             "PLAN|2\nPGROUP\nLOOP|2\nWHEEL|1\nENDLOOP\nPARITEM\nWHEEL|2\nENDPAR",
             "not allowed inside PGROUP")
expect_error("PGROUP needs at least two branches",
             "PLAN|2\nPGROUP\nWHEEL|1\nENDPAR", "at least two branches")

# -- buzzer -----------------------------------------------------------------
c = run("PLAN|2\nBEEP|880,120")
check("BEEP reaches the buzzer", ("beep", 880, 120) in c.ev)
expect_error("BEEP rejects an out-of-range tone", "PLAN|2\nBEEP|10,100", "out of range")
expect_error("BEEP needs freq,ms", "PLAN|2\nBEEP|880", "needs freq,ms")
try:
    cc = CtxNoBeep()
    pe.run_plan(pe.parse_plan("PLAN|2\nBEEP|880,120"), cc)
except ValueError as exc:
    check("BEEP on old firmware fails loudly", "plan_api>=3" in str(exc))
else:
    check("BEEP on old firmware fails loudly", False)

# -- keypad gate (GP3 pause / GP4 stop) -------------------------------------
c = run("PLAN|2\nDELAY|1\nDELAY|2\nDELAY|3")
check("gate is polled before every op", c.gates == 4)

c = Ctx(stop_at=3)
try:
    pe.run_plan(pe.parse_plan("PLAN|2\nDELAY|1\nDELAY|2\nDELAY|3"), c)
except pe.PlanAbort:
    check("GP4 stop aborts mid-plan", delays(c) == [1] and ("stopped",) in c.ev)
else:
    check("GP4 stop aborts mid-plan", False)

c = run("PLAN|2\nDELAY|1\nDELAY|2", pause_for=3)
check("GP3 pause holds the plan, then it resumes",
      c.ev.count(("paused",)) == 3 and delays(c) == [1, 2])

c = Ctx(stop_at=2)
try:
    pe.run_plan(pe.parse_plan("PLAN|2\nLOOP|1000\nDELAY|1\nENDLOOP"), c)
except pe.PlanAbort:
    check("GP4 stop escapes a long loop", True)
else:
    check("GP4 stop escapes a long loop", False)

# -- Win+R launcher macros ---------------------------------------------------
def typed(lines):
    for ln in lines:
        if ln.startswith("TYPE|text="):
            return pe.pct_dec(ln[len("TYPE|text="):])
    return None


def parses(lines):
    pe.parse_plan("PLAN|2\n" + "\n".join(lines))
    return True


vis = winr.launch(r"C:\Tools\my app.exe", mode="visible")
check("visible launcher types the quoted path", typed(vis) == '"C:\\Tools\\my app.exe"')
check("visible launcher is a valid plan", parses(vis))

mini = winr.launch(r"C:\Tools\app.exe", mode="min")
check("minimised launcher uses start /min",
      typed(mini) == 'cmd /c start /min "" C:\\Tools\\app.exe')

hid = winr.launch(r"C:\Tools\app.exe", args="-q", mode="hidden")
htxt = typed(hid)
check("hidden launcher hides the PowerShell host", htxt.startswith("powershell -w hidden -c"))
check("hidden launcher hides the child window", "-WindowStyle Hidden" in htxt)
check("hidden launcher passes arguments", "-ArgumentList '-q'" in htxt)
check("hidden launcher wipes the Run history", "RunMRU" in htxt)
check("hidden launcher is a valid plan", parses(hid))
check("launcher presses Win+R then Enter",
      "KEY|combo=91+82|hold=40,90" in hid and "KEY|combo=13|hold=40,90" in hid)

keep = winr.launch(r"C:\Tools\app.exe", mode="hidden", clean_mru=False)
check("Run history cleanup can be turned off", "RunMRU" not in typed(keep))

opn = winr.launch(r"C:\docs\report.pdf", mode="hidden", shell_open=True)
check("openFile uses the file association", "-WindowStyle Hidden" not in typed(opn))

wav = winr.audio(r"C:\snd\ding.wav")
check("wav audio plays with no window", "Media.SoundPlayer" in typed(wav))
check("wav audio is a valid plan", parses(wav))
mp3 = winr.audio(r"C:\snd\track.mp3", seconds=5)
check("mp3 audio uses MediaPlayer with a hold",
      "MediaPlayer" in typed(mp3) and "Start-Sleep -Seconds 5" in typed(mp3))

pin = winr.pinned(3)
check("pinned launcher is Win+3 with no Run box",
      "KEY|combo=91+51|hold=40,90" in pin and not any("TYPE" in l for l in pin))
check("pinned launcher is a valid plan", parses(pin))

gated = winr.launch(r"C:\Tools\app.exe", mode="hidden", gate="20,900,120,8000,0")
check("light gate wraps the launcher",
      gated.count("WLIGHT|20,900,120,8000,0") == 2 and parses(gated))

try:
    winr.launch("C:\\\u0628\u0631\u0646\u0627\u0645\u0647\\app.exe", mode="hidden")
except ValueError as exc:
    check("non-ASCII path is refused with advice", "pinned taskbar icon" in str(exc))
else:
    check("non-ASCII path is refused with advice", False)

check("pipe and percent are percent-encoded",
      winr.pct("a|b%c") == "a%7Cb%25c")

print("=== Results: %d passed, %d failed ===" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
