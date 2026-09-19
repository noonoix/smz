#!/usr/bin/env python3
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
for old,new in {
'raise GuardBundleError("unvalidated route")':'raise runtime.GuardBundleError("unvalidated route")',
'    if persist or any(kind.startswith(prefix) for prefix in _DEBUG_PERSIST_EVENTS):\n        _debug_persist(self)':'    if kind in ("BOOT", "FAIL"):\n        _debug_persist(self)',
}.items():
    if old in s: s=s.replace(old,new)
    elif new not in s: raise SystemExit('missing anchor: '+old)
block='''_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP"}


def _light_route_file(name):
    # Scan without reading the complete route into RAM.
    with open("/" + name, "r") as fh:
        while True:
            raw = fh.readline()
            if not raw:
                return True
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            split = line.find("|")
            if split < 1 or line[:split].upper() not in _LIGHT_ROUTE_COMMANDS:
                return False


def _light_gate(ctx, expected_state):
    owner = ctx.r
    owner.host_poll(); owner.buttons(); owner.arm.pump()
    while owner.controls.paused and owner.controls.running:
        owner.host_poll(); owner.buttons(); owner.arm.pump(); runtime.time.sleep(.01)
    if not owner.controls.running or owner.calibrating:
        return False
    now = runtime.time.monotonic()
    if now >= getattr(ctx, "_light_poll_due", 0):
        ctx._light_poll_due = now + .25
        if owner.guard.update(owner.sensor.lux(), int(now * 1000)) != expected_state:
            return False
    return True


def _light_sleep(ctx, milliseconds, expected_state):
    end = runtime.time.monotonic() + max(0, milliseconds) / 1000
    while runtime.time.monotonic() < end:
        if not _light_gate(ctx, expected_state): return False
        runtime.time.sleep(.005)
    return True


def _run_light_route(ctx, name):
    # Stream each command from flash. This avoids the text, tuple list and loop
    # link table allocations that exhausted the Pico heap at ROUTE/start.
    gc.collect()
    expected = getattr(ctx.r, "debug_last_state", None)
    ctx._light_poll_due = 0
    frames = []
    with open("/" + name, "r") as fh:
        while True:
            if not _light_gate(ctx, expected): return
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
                a = args.split(","); ctx.screen_w, ctx.screen_h = int(a[0]), int(a[1])
            elif op == "SPEED":
                a = args.split(","); ctx.speed_min, ctx.speed_max = int(a[0]), int(a[1])
            elif op == "DELAY":
                a = args.split(","); ms = int(a[0])
                if not _light_sleep(ctx, ms, expected): return
            elif op == "BEEP":
                a = args.split(",")
                if len(a) != 2: raise ValueError("BEEP needs frequency,duration")
                ctx.beep(int(a[0]), int(float(a[1])))
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
    if name not in self.bundle["manifest"]["routes"].values():
        raise runtime.GuardBundleError("unvalidated route")
    if name not in self.routes:
        gc.collect()
        if _light_route_file(name):
            self.routes[name] = "light"
        else:
            with open("/" + name, "r") as fh:
                text = fh.read()
            self.routes[name] = ("plan", runtime.plan_engine.parse_plan(text))
    route = self.routes[name]
    if route == "light":
        _run_light_route(runtime.PlanContext(self), name)
    else:
        runtime.plan_engine.run_plan(route[1], runtime.PlanContext(self))
    self.arm.flush()

runtime.Combined.route = _diagnostic_route
'''
start=s.find('_LIGHT_ROUTE_COMMANDS =')
marker='runtime.Combined.route = _diagnostic_route'
end=s.find(marker,start)
if start<0 or end<0: raise SystemExit('missing light route region')
end=s.find('\n',end)
if end<0: end=len(s)
else: end+=1
s=s[:start]+block+s[end:]
if s.count('def _light_gate(ctx, expected_state):')!=1: raise SystemExit('duplicate gate')
if s.count('def _diagnostic_route(self, decision):')!=1: raise SystemExit('duplicate route')
p.write_text(s,encoding='utf-8',newline='\n')
print('patched',p)
