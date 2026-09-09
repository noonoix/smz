#!/usr/bin/env python3
# code64b_check.py - integrity + behaviour checks for code64b.py (real code slices
# exec'd against fake hardware). Runs on PC: python code64b_check.py
# v0.9.64b - updated for CONDITIONAL button release (the stop/start teleport fix):
# routine GP4 start/stop with no held button must write ZERO MUPs (arm fw>=1.8 syncs
# its tracked axes into every button report, so each pointless MUP teleported the
# cursor to the last plan point - record 2026-09-09: 5 snaps of 964-1216 px).
# Retractions vs code64_check: old T1c/T2 asserted unconditional MUP x3 on every
# start/stop; that behaviour was the bug and is now inverted by design. The full
# three-button shield survives on the abnormal paths (force=True) and via the panic
# gesture (GP4 held >= 1 s).
import ast, os, sys

SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "code64b.py"), encoding="utf-8").read()

results = []
def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)

def extract(src, name):
    lines = src.splitlines(True)
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "".join(lines[node.lineno - 1:node.end_lineno]) + "\n"
    raise ValueError("function not found: " + name)

# ---------- static wiring assertions ----------
check("S1 banner v0.9.64b", "# Classroom Studio v0.9.64b" in SRC)
check("S2 PONG reports 0.9.64b", "OK|PONG|pico-light 0.9.64b|" in SRC)
check("S3 watchdog constant", "ARM_ACK_TIMEOUT = 1.0" in SRC and "ARM_LAG_MAX = 8" in SRC)
pk = extract(SRC, "poll_keypad")
se = extract(SRC, "start_engine")
pu = extract(SRC, "pump_arm")
rb = extract(SRC, "release_all_buttons")
ff = extract(SRC, "forward_fast")
check("S4 start_engine resets passes + ledger", "passes = 0" in se and "_flow_reset()" in se and "global passes" in se)
check("S5 GP4 start edge calls start_engine before NumLock echo",
      "start_engine()" in pk and pk.index("start_engine()") < pk.index("tap_key(Keycode.KEYPAD_NUMLOCK)"))
check("S6 pump_arm has watchdog feeding + self-heal",
      "_arm_last_ack = time.monotonic()" in pu and "ARM_ACK_TIMEOUT" in pu and "ack watchdog reset" in pu)
check("S7 run errors ALWAYS printed", '        print("plan: run error:", exc)' in SRC)
check("S8 boot banner 0.9.64b + fault flashes", 'print("pico-light 0.9.64b' in SRC and "led_fault(2)" in SRC and "led_fault(3)" in SRC)
check("S9 conditional release: force param + tracked targets",
      "def release_all_buttons(force=False):" in rb
      and 'targets = ("left", "right", "middle") if force else tuple(sorted(_held_buttons))' in rb
      and "_held_buttons.clear()" in rb)
check("S10 routine start/stop stay conditional (exactly 2 bare call sites, comments excluded)",
      sum(1 for l in SRC.splitlines() if "release_all_buttons()" in l and not l.lstrip().startswith("#")) == 2
      and "release_all_buttons()" in se and "release_all_buttons()" in pk)
check("S11 full shield on abnormal paths (abort + error + HALT/BYE + panic)",
      SRC.count("release_all_buttons(force=True)") >= 4)
check("S12 code64 context exposes persistent mouse position",
      "def get_mouse_pos(self):" in SRC and "def set_mouse_pos(self, x, y):" in SRC
      and "_plan_mouse_pos = None" in SRC)
check("S13 start_engine preserves saved mouse position", "_plan_mouse_pos =" not in se)
check("S16 held-button tracking lives in forward_fast (MDOWN add / MUP discard)",
      '_held_buttons.add(' in ff and '_held_buttons.discard(' in ff and 'head == "MDOWN"' in ff and 'head == "MUP"' in ff)
check("S17 panic gesture: GP4 hold >= 1 s force-releases + 5 flashes",
      "_btn1_since = time.monotonic()" in pk and ">= 1.0" in pk and "led_fault(5)" in pk and "_btn1_since" in pk)

PE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_engine.py")
PE_SRC = open(PE_PATH, encoding="utf-8").read()
check("S14 plan engine loads and saves cursor state",
      "_load_mouse_pos(ctx, ops)" in PE_SRC and "_save_mouse_pos(ctx, pos)" in PE_SRC)
check("S15 every sent MMOVE persists before abortable delay",
      PE_SRC.index("_save_mouse_pos(ctx, pos)", PE_SRC.index("for pt in plan"))
      < PE_SRC.index("if not ctx.sleep_ms(pt[2])", PE_SRC.index("for pt in plan")))

# ---------- behavioural tests (real code slices, fake hardware) ----------
class FakeTime:
    def __init__(self): self.t = 100.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s

class FakeBtn:
    def __init__(self): self.value = True        # active-low wiring: True = released

class FakeLed:
    def __init__(self): self.value = False

class FakeArm:
    def __init__(self): self.rx = bytearray(); self.tx = []
    @property
    def in_waiting(self): return len(self.rx)
    def read(self, n):
        out = bytes(self.rx[:n]); del self.rx[:n]; return out
    def write(self, b): self.tx.append(b.decode()); return len(b)

FT = FakeTime()
PRINTS = []
TAPS = []
ns = {
    "time": FT, "Keycode": type("KC", (), {"KEYPAD_NUMLOCK": "NUM", "SCROLL_LOCK": "SCR"}),
    "tap_key": lambda code: TAPS.append(code),
    "btn1": FakeBtn(), "btn2": FakeBtn(), "led": FakeLed(),
    "engine_on": False, "engine_paused": False, "_last_btn1": True, "_last_btn2": True,
    "_btn1_since": None,
    "passes": 0, "started": 0.0,
    "LOOP_MODE": "once", "LOOP_COUNT": 0, "LOOP_SECONDS": 0,
    "arm": FakeArm(), "_arm_buf": bytearray(),
    "_arm_lag": 0, "_pending_move": None, "_arm_last_ack": FT.t,
    "ARM_LAG_MAX": 8, "ARM_ACK_TIMEOUT": 1.0,
    "MOUSE_PREFIXES": ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP"),
    "_held_buttons": set(),
    "_serial_write_line": lambda s: None,
    "print": lambda *a: PRINTS.append(" ".join(str(x) for x in a)),
}
for fn in ("_flow_reset", "release_all_buttons", "start_engine", "led_fault", "poll_keypad",
           "pump_arm", "forward_fast", "_arm_write", "loop_due"):
    exec(extract(SRC, fn), ns)

MUPS = ["MUP|left\n", "MUP|right\n", "MUP|middle\n"]

def press_btn1(hold_s=0.0):
    ns["btn1"].value = False; ns["poll_keypad"]()
    if hold_s: FT.t += hold_s
    ns["btn1"].value = True;  ns["poll_keypad"]()

# baseline poll converts the boot sentinels (_last_btn*=True) to the released state
ns["poll_keypad"]()

# T1 - once-trap fix + start re-arm
ns["engine_on"] = False; ns["engine_paused"] = False
ns["passes"] = 1; ns["_arm_lag"] = 6; ns["_pending_move"] = "MMOVE|1,2,abs,2"
check("T1 stale once-pass blocks a run before the fix (loop_due False)", ns["loop_due"]() is False)
tx0 = len(ns["arm"].tx)
press_btn1()
check("T1b GP4 start re-arms: engine on, passes=0, ledger wiped, loop_due True, NumLock echoed",
      ns["engine_on"] is True and ns["passes"] == 0 and ns["_arm_lag"] == 0
      and ns["_pending_move"] is None and ns["loop_due"]() is True and TAPS == ["NUM"])
check("T1c v0.9.64b - start with NO held button writes ZERO MUPs (no cursor_sync teleport) + LED solid",
      ns["arm"].tx[tx0:] == [] and ns["led"].value is True)

# T2 - stop edge with no held button writes nothing either
press_btn1()
check("T2 v0.9.64b - GP4 stop: engine off, pause cleared, echo, LED off, ZERO MUPs",
      ns["engine_on"] is False and ns["engine_paused"] is False and TAPS == ["NUM", "NUM"]
      and ns["led"].value is False and ns["arm"].tx == [])

# T2b - a genuinely held button IS released on start (the v0.9.63 shield, now precise)
r = ns["forward_fast"]("MDOWN|left")
tx0 = len(ns["arm"].tx)
press_btn1()   # start
check("T2b held MDOWN|left is tracked and released on start (exactly one MUP|left)",
      r == "OK|MDOWN" and ns["arm"].tx[tx0:] == ["MUP|left\n"] and len(ns["_held_buttons"]) == 0)

# T2c - force=True always releases all three, even with an empty held set
ns["arm"].tx = []
ns["release_all_buttons"](True)
check("T2c force=True keeps the full v0.9.63 shield (MUP x3)", ns["arm"].tx == MUPS)

# T2d - panic gesture: GP4 held >= 1 s force-releases all three (engine toggles too)
ns["arm"].tx = []
ns["engine_on"] = False
press_btn1(hold_s=1.2)
check("T2d panic hold (>=1 s): full MUP x3 fired on the release edge",
      ns["arm"].tx[-3:] == MUPS and ns["engine_on"] is True)

# T3 - coalescing ceiling regression guard
ns["engine_on"] = True
ns["_arm_lag"] = 8; ns["_pending_move"] = None; ns["_arm_last_ack"] = FT.t
tx0 = len(ns["arm"].tx)
r = ns["forward_fast"]("MMOVE|100,200,abs,2")
check("T3a at lag=8 an MMOVE coalesces (no write, newest kept)",
      r is None and ns["_pending_move"] == "MMOVE|100,200,abs,2" and len(ns["arm"].tx) == tx0)
ns["arm"].rx += b"OK|MMOVE\n"
ns["pump_arm"]()
check("T3b one ack flushes the coalesced target (tx + lag restored to 8)",
      ns["arm"].tx[-1] == "MMOVE|100,200,abs,2\n" and ns["_pending_move"] is None and ns["_arm_lag"] == 8)

# T4 - watchdog self-heals after 2 s of ack silence
ns["_arm_lag"] = 5; ns["_pending_move"] = "MMOVE|300,400,abs,2"
FT.t += 2.0
PRINTS.clear()
ns["pump_arm"]()
check("T4 ack watchdog fires: prints, flushes newest target, ledger re-synced to 1",
      any("ack watchdog reset" in p for p in PRINTS) and ns["_pending_move"] is None
      and ns["_arm_lag"] == 1 and ns["arm"].tx[-1] == "MMOVE|300,400,abs,2\n")

# T5 - no fire while acks are fresh
PRINTS.clear()
ns["_arm_lag"] = 3; ns["_pending_move"] = None; ns["_arm_last_ack"] = FT.t
ns["pump_arm"]()
check("T5 fresh acks: watchdog stays quiet, lag untouched",
      ns["_arm_lag"] == 3 and not any("watchdog" in p for p in PRINTS))

# T6 - an ack feeds the watchdog clock and drains lag
ns["arm"].rx += b"OK|MMOVE\n"
ns["pump_arm"]()
check("T6 OK|MMOVE: lag 3->2 and _arm_last_ack refreshed",
      ns["_arm_lag"] == 2 and ns["_arm_last_ack"] == FT.t)

# T7 - paused engine: watchdog drops the stale pending instead of a surprise jump
ns["engine_paused"] = True
ns["_arm_lag"] = 4; ns["_pending_move"] = "MMOVE|9,9,abs,2"
tx0 = len(ns["arm"].tx)
FT.t += 2.0
ns["pump_arm"]()
check("T7 watchdog while paused: pending dropped, nothing written, lag zeroed",
      ns["_pending_move"] is None and ns["_arm_lag"] == 0 and len(ns["arm"].tx) == tx0)

# T8 - GP3 toggles pause + Scroll Lock echo, with zero arm traffic (no panic side effects)
ns["engine_paused"] = False
tx0 = len(ns["arm"].tx)
ns["btn2"].value = False; FT.t += 1.5; ns["poll_keypad"]()
ns["btn2"].value = True;  ns["poll_keypad"]()
check("T8 GP3 pause toggle + Scroll Lock echo, no MUP/panic side effects",
      ns["engine_paused"] is True and TAPS[-1] == "SCR" and len(ns["arm"].tx) == tx0)

# T9/T10 - real plan_engine position persistence across restart and mid-path Stop
import importlib.util
spec = importlib.util.spec_from_file_location("pe64bcheck", PE_PATH)
PE = importlib.util.module_from_spec(spec); spec.loader.exec_module(PE)

class PlanCtx:
    screen_w=1920; screen_h=1080; speed_min=0; speed_max=2000
    def __init__(self, saved=None, sleeps=None):
        self.saved=saved; self.sent=[]; self.sleeps=list(sleeps or [])
    def get_mouse_pos(self): return self.saved
    def set_mouse_pos(self,x,y): self.saved=(x,y)
    def now(self): return 0.0
    def log(self,msg): pass
    def sleep_ms(self,ms): return self.sleeps.pop(0) if self.sleeps else True
    def mmove(self,x,y): self.sent.append((x,y))
    def mclick(self,*a): pass
    def ktext(self,*a): pass
    def kcombo(self,*a): pass
    def wait_light(self,*a): return False
    def key(self,*a): pass

rmouse=("RMOUSE", {"region":(1301,0,5,5)})
ops=[("SCREEN", {"v":(1920,1080)}), rmouse]
calls=[]
def fake_plan(sx,sy,tx,ty,c,pauses,sw,sh):
    calls.append((sx,sy,tx,ty))
    return {"pts":[(tx,ty,0)], "target":(tx,ty), "before":0, "after":0, "long":0}
PE.plan_move=fake_plan
pc=PlanCtx()
PE.run_plan(ops,pc)
saved1=pc.saved
PE.run_plan(ops,pc)
check("T9 restart begins at previous target, not screen centre",
      calls[0][:2] == (960,540) and calls[1][:2] == saved1 and saved1 != (960,540))

abort_calls=[]
def abort_plan(sx,sy,tx,ty,c,pauses,sw,sh):
    abort_calls.append((sx,sy))
    return {"pts":[(410,310,1),(420,320,1)], "target":(420,320),
            "before":0, "after":0, "long":0}
PE.plan_move=abort_plan
pc2=PlanCtx(saved=(400,300), sleeps=[True,False])
try: PE.run_plan(ops,pc2)
except PE.PlanAbort: pass
check("T10a Stop mid-path saves last MMOVE before abort", pc2.saved==(410,310) and pc2.sent==[(410,310)])
pc2.sleeps=[]; pc2.sent=[]
PE.run_plan(ops,pc2)
check("T10b next Start resumes from last MMOVE", abort_calls[-1]==(410,310))

failed = [n for n, ok in results if not ok]
print("\ncode64b_check: %d/%d pass" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
