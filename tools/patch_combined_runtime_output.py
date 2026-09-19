#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
for old,new in {
'raise GuardBundleError("unvalidated route")':'raise runtime.GuardBundleError("unvalidated route")',
'    if persist or any(kind.startswith(prefix) for prefix in _DEBUG_PERSIST_EVENTS):\n        _debug_persist(self)':'    if kind in ("BOOT", "FAIL"):\n        _debug_persist(self)',
}.items():
    if old in s: s=s.replace(old,new)
    elif new not in s: raise SystemExit('missing anchor: '+old)
block='''_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP"}


def _light_gate(owner, expected_state):
    owner.host_poll(); owner.buttons(); owner.arm.pump()
    while owner.controls.paused and owner.controls.running:
        owner.host_poll(); owner.buttons(); owner.arm.pump(); runtime.time.sleep(.01)
    if not owner.controls.running or owner.calibrating:
        return False
    now = runtime.time.monotonic()
    if now >= getattr(owner, "light_poll_due", 0):
        owner.light_poll_due = now + .25
        if owner.guard.update(owner.sensor.lux(), int(now * 1000)) != expected_state:
            return False
    return True


def _light_sleep(owner, milliseconds, expected_state):
    end = runtime.time.monotonic() + max(0, milliseconds) / 1000
    while runtime.time.monotonic() < end:
        if not _light_gate(owner, expected_state): return False
        runtime.time.sleep(.005)
    return True


def _light_beep(owner, frequency, duration, expected_state):
    tone = runtime.pwmio.PWMOut(runtime.board.GP6, duty_cycle=32768,
        frequency=int(frequency), variable_frequency=True)
    try:
        return _light_sleep(owner, duration, expected_state)
    finally:
        tone.duty_cycle = 0
        tone.deinit()


def _run_light_route(owner, name):
    # No PlanContext, route cache, whole-file read, command list or link table.
    gc.collect()
    owner.emit("EVT|DEBUG|MEM/route-enter free=%d" % gc.mem_free())
    expected = getattr(owner, "debug_last_state", None)
    owner.light_poll_due = 0
    frames = []
    with open("/" + name, "r") as fh:
        owner.emit("EVT|DEBUG|MEM/route-open free=%d" % gc.mem_free())
        while True:
            if not _light_gate(owner, expected): return
            raw = fh.readline()
            if not raw:
                if frames: raise ValueError("LOOP without ENDLOOP")
                return
            line = raw.strip()
            if not line or line.startswith("#"): continue
            split = line.find("|")
            if split < 1: raise ValueError("invalid route line")
            op = line[:split].upper(); args = line[split + 1:]
            if op == "PLAN":
                if args != "2": raise ValueError("unsupported PLAN version")
            elif op == "SCREEN":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SCREEN")
            elif op == "SPEED":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SPEED")
            elif op == "DELAY":
                a = args.split(",")
                if not _light_sleep(owner, int(a[0]), expected): return
            elif op == "BEEP":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad BEEP")
                owner.emit("EVT|DEBUG|STEP/BEEP %s,%s" % (a[0], a[1]))
                if not _light_beep(owner, int(a[0]), int(float(a[1])), expected): return
            elif op in ("LOOP", "LOOPTIME"):
                body = fh.tell()
                if op == "LOOP":
                    value = int(args or "1")
                    if value < 0: raise ValueError("negative LOOP")
                    frames.append([body, value, 0])
                else:
                    sec = float(args or "0")
                    if sec <= 0: raise ValueError("bad LOOPTIME")
                    frames.append([body, -1, runtime.time.monotonic() + sec])
            elif op == "ENDLOOP":
                if not frames: raise ValueError("ENDLOOP without LOOP")
                frame = frames[-1]
                if frame[1] < 0:
                    if runtime.time.monotonic() < frame[2]: fh.seek(frame[0])
                    else: frames.pop()
                elif frame[1] == 0:
                    fh.seek(frame[0])
                else:
                    frame[1] -= 1
                    if frame[1] > 0: fh.seek(frame[0])
                    else: frames.pop()
            else:
                raise ValueError("unsupported light command")


def _diagnostic_route(self, decision):
    if not decision.get("execute"):
        return
    name = decision.get("route")
    if name not in runtime.PROFILE_TO_ROUTE.values():
        raise runtime.GuardBundleError("unvalidated route")
    _run_light_route(self, name)
    self.arm.flush()

runtime.Combined.route = _diagnostic_route
'''
start=s.find('_LIGHT_ROUTE_COMMANDS =')
marker='runtime.Combined.route = _diagnostic_route'
end=s.find(marker,start)
if start<0 or end<0: raise SystemExit('missing light region')
end=s.find('\n',end); end=len(s) if end<0 else end+1
s=s[:start]+block+s[end:]
release='''                self.guard_start_tone()
                self.bundle = None
                self.guard.bundle = None
                gc.collect()
                _debug_event(self, "GP4", "short-start running=1 free=%d" % gc.mem_free(), persist=True)'''
old='''                self.guard_start_tone()
                _debug_event(self, "GP4", "short-start running=1", persist=True)'''
if old in s: s=s.replace(old,release,1)
elif release not in s: raise SystemExit('missing short-start anchor')
helper='''def _ensure_runtime_bundle(self):
    if self.bundle is None:
        self.bundle = runtime.load_guard_bundle("/")
        self.guard.bundle = self.bundle
        gc.collect()

'''
anchor='def _enter_calibration_from_pending_start(self):\n'
if helper not in s:
    if anchor not in s: raise SystemExit('missing calibration anchor')
    s=s.replace(anchor,helper+anchor,1)
s=s.replace('def _enter_calibration_from_pending_start(self):\n    #', 'def _enter_calibration_from_pending_start(self):\n    _ensure_runtime_bundle(self)\n    #',1)
s=s.replace('def _audible_start_cal(self):\n    _original_start_cal(self)', 'def _audible_start_cal(self):\n    _ensure_runtime_bundle(self)\n    _original_start_cal(self)',1)
if s.count('def _run_light_route(owner, name):')!=1: raise SystemExit('bad runner count')
p.write_text(s,encoding='utf-8',newline='\n')
print('patched',p)
