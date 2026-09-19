#!/usr/bin/env python3
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
for old,new in {
'raise GuardBundleError("unvalidated route")':'raise runtime.GuardBundleError("unvalidated route")',
'_run_light_route(PlanContext(self), route)':'_run_light_route(runtime.PlanContext(self), route)',
'runtime.plan_engine.run_plan(route, PlanContext(self))':'runtime.plan_engine.run_plan(route, runtime.PlanContext(self))',
'    if persist or any(kind.startswith(prefix) for prefix in _DEBUG_PERSIST_EVENTS):\n        _debug_persist(self)':'    if kind in ("BOOT", "FAIL"):\n        _debug_persist(self)',
}.items():
    if old in s: s=s.replace(old,new)
    elif new not in s: raise SystemExit('missing anchor: '+old)
s,n=re.subn(r'_LIGHT_ROUTE_COMMANDS = \{[^\n]+\}', '_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP"}', s, count=1)
if n!=1: raise SystemExit('missing command set')
runner='''def _light_gate(ctx, expected_state):
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


def _light_end(commands, start):
    depth = 1
    pos = start + 1
    while pos < len(commands):
        op = commands[pos][0]
        if op in ("LOOP", "LOOPTIME"): depth += 1
        elif op == "ENDLOOP":
            depth -= 1
            if depth == 0: return pos
        pos += 1
    raise ValueError("LOOP without ENDLOOP")


def _run_light_route(ctx, commands):
    gc.collect()
    expected = getattr(ctx.r, "debug_last_state", None)
    ctx._light_poll_due = 0
    frames = []
    pc = 0
    while pc < len(commands):
        if not _light_gate(ctx, expected): return
        op, args = commands[pc]
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
            end = _light_end(commands, pc)
            if op == "LOOP":
                value = int(args or "1")
                if value < 0: raise ValueError("negative LOOP")
                frames.append([pc, end, value, 0])
            else:
                sec = float(args or "0")
                if sec <= 0: raise ValueError("bad LOOPTIME")
                frames.append([pc, end, -1, runtime.time.monotonic() + sec])
        elif op == "ENDLOOP":
            if not frames or frames[-1][1] != pc: raise ValueError("ENDLOOP without LOOP")
            f = frames[-1]
            if f[2] < 0:
                if runtime.time.monotonic() < f[3]: pc=f[0]+1; continue
                frames.pop()
            elif f[2] == 0:
                pc=f[0]+1; continue
            else:
                f[2]-=1
                if f[2] > 0: pc=f[0]+1; continue
                frames.pop()
        pc += 1

'''
start=s.find('def _light_gate(ctx, expected_state):')
if start < 0: start=s.find('def _run_light_route(ctx, commands):')
end=s.find('def _diagnostic_route(self, decision):')
if start < 0 or end <= start: raise SystemExit('missing runner region')
s=s[:start]+runner+s[end:]
s=s.replace('    if name not in self.routes:\n        with open("/" + name, "r") as fh:', '    if name not in self.routes:\n        gc.collect()\n        with open("/" + name, "r") as fh:', 1)
if s.count('def _light_gate(ctx, expected_state):') != 1: raise SystemExit('duplicate light gate')
if s.count('def _run_light_route(ctx, commands):') != 1: raise SystemExit('duplicate light runner')
p.write_text(s,encoding='utf-8',newline='\n')
print('patched',p)
