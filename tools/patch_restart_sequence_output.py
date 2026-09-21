#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
init_old='''    self.debug_last_state = None
    _debug_event(self, "BOOT", "bundle=valid profiles=%d" % len(runtime.PROFILES), persist=True)'''
init_new='''    self.debug_last_state = None
    self.restart_cycle_started = None
    self.restart_deadline = None
    self.restart_waiting = _restart_marker_exists()
    self.restart_down_seen = bool(self.restart_waiting)
    self.restart_up_since = None
    self.restart_route_pending = False
    _debug_event(self, "BOOT", "bundle=valid profiles=%d restart=%d" % (len(runtime.PROFILES), 1 if self.restart_waiting else 0), persist=True)'''
if init_old in s: s=s.replace(init_old,init_new,1)
elif init_new not in s: raise SystemExit('missing restart init anchor')
helper=r'''_RESTART_MARKER = "/.combined_restart_pending"

def _restart_marker_exists():
    try:
        with open(_RESTART_MARKER, "r") as fh: return fh.read().strip() == "1"
    except Exception: return False

def _restart_marker_set():
    try:
        try: runtime.storage.remount("/", readonly=False, disable_concurrent_write_protection=True)
        except Exception: pass
        with open(_RESTART_MARKER, "w") as fh: fh.write("1")
        return _restart_marker_exists()
    except Exception: return False

def _restart_marker_clear():
    try: runtime.os.remove(_RESTART_MARKER)
    except Exception: pass

def _restart_range():
    try:
        with open("/plan.txt", "r") as fh:
            for raw in fh:
                if raw.startswith("RUNFOR|"):
                    a=raw.strip().split("|",1)[1].split(",")
                    lo=int(a[0]); hi=int(a[1])
                    if hi<lo: lo,hi=hi,lo
                    if lo>0: return lo,hi
    except Exception: pass
    return 6600,7800

def _restart_tap(owner, code, lo, hi):
    owner.keyboard.press(code)
    try: owner.controls.sleep(_light_random.randint(lo,hi))
    finally: owner.keyboard.release(code)

def _restart_windows(owner):
    owner.keyboard.press(227); owner.controls.sleep(_light_random.randint(25,60))
    owner.keyboard.press(27); owner.controls.sleep(_light_random.randint(45,95)); owner.keyboard.release(27)
    owner.controls.sleep(_light_random.randint(25,60)); owner.keyboard.release(227)
    owner.controls.sleep(_light_random.randint(450,850))
    for code,hold,after in ((82,(45,100),(110,240)),(82,(45,100),(180,360)),(40,(55,120),(280,520)),(82,(45,100),(350,700)),(40,(55,120),None)):
        _restart_tap(owner,code,hold[0],hold[1])
        if after: owner.controls.sleep(_light_random.randint(after[0],after[1]))
    owner.controls.sleep(_light_random.randint(5200,6000))
    owner.keyboard.press(225); owner.controls.sleep(_light_random.randint(320,480))
    _restart_tap(owner,43,160,240); owner.controls.sleep(_light_random.randint(180,300)); owner.keyboard.release(225)
    owner.controls.sleep(_light_random.randint(300,650)); _restart_tap(owner,40,65,130)

def _restart_tick(owner):
    now=runtime.time.monotonic()
    if owner.restart_waiting:
        connected=bool(runtime.supervisor.runtime.usb_connected)
        if not connected:
            owner.restart_down_seen=True; owner.restart_up_since=None; return
        if not owner.restart_down_seen: return
        if owner.restart_up_since is None: owner.restart_up_since=now; return
        if now-owner.restart_up_since < 12: return
        owner.restart_waiting=False; owner.restart_route_pending=True
        owner.controls.start(); owner.guard.reset(); owner.debug_last_state=None
        _debug_event(owner,"RESTART","host-up route-pending=1",persist=True); return
    if not owner.controls.running or owner.restart_route_pending: return
    if owner.restart_cycle_started is None:
        lo,hi=_restart_range(); owner.restart_cycle_started=now
        owner.restart_deadline=now+(lo if hi<=lo else _light_random.randint(lo,hi))
        _debug_event(owner,"RESTART","deadline=%d"%int(owner.restart_deadline),persist=True); return
    if now < owner.restart_deadline: return
    if not _restart_marker_set(): raise RuntimeError("restart marker write failed")
    _debug_event(owner,"RESTART","armed",persist=True)
    owner.keyboard.release_all(); _restart_windows(owner)
    owner.controls.running=False; owner.restart_waiting=True
    owner.restart_down_seen=False; owner.restart_up_since=None

'''
anchor='def _diagnostic_route(self, decision):\n'
if helper not in s:
    if anchor not in s: raise SystemExit('missing restart helper anchor')
    s=s.replace(anchor,helper+anchor,1)
s=s.replace('''            if not _light_gate(owner, expected): return
            raw = fh.readline()
            if not raw:
                if frames: raise ValueError("LOOP without ENDLOOP")
                return''','''            if not _light_gate(owner, expected): return False
            raw = fh.readline()
            if not raw:
                if frames: raise ValueError("LOOP without ENDLOOP")
                return True''',1)
route_old='''    primary = None
    try:
        return _run_light_route(self, name)
    except Exception as exc:'''
route_new='''    primary = None
    try:
        if name == "desktop_steps.txt" and self.restart_route_pending:
            _debug_event(self, "ROUTE", "restart-before-desktop", persist=True)
            if not _run_light_route(self, "restart_steps.txt"): return False
            self.restart_route_pending = False
            _restart_marker_clear()
            self.restart_cycle_started = runtime.time.monotonic()
            lo, hi = _restart_range()
            self.restart_deadline = self.restart_cycle_started + (lo if hi <= lo else _light_random.randint(lo, hi))
            _debug_event(self, "ROUTE", "restart-complete desktop-next", persist=True)
        _run_light_route(self, name)
    except Exception as exc:'''
if route_old in s: s=s.replace(route_old,route_new,1)
elif route_new not in s: raise SystemExit('missing restart route anchor')
loop_old='''        self.arm.pump()
        if (self.controls.running and not self.calibrating and'''
loop_new='''        self.arm.pump()
        _restart_tick(self)
        if (self.controls.running and not self.calibrating and'''
if loop_old in s: s=s.replace(loop_old,loop_new,1)
elif loop_new not in s: raise SystemExit('missing restart tick anchor')
p.write_text(s,encoding='utf-8',newline='\n'); print('patched',p)
