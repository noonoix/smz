#!/usr/bin/env python3
"""Idempotently patch the Combined Guard runtime packaged by Classroom Studio."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacements = {
    'raise GuardBundleError("unvalidated route")': 'raise runtime.GuardBundleError("unvalidated route")',
    '_run_light_route(PlanContext(self), route)': '_run_light_route(runtime.PlanContext(self), route)',
    'runtime.plan_engine.run_plan(route, PlanContext(self))': 'runtime.plan_engine.run_plan(route, runtime.PlanContext(self))',
    '    if persist or any(kind.startswith(prefix) for prefix in _DEBUG_PERSIST_EVENTS):\n        _debug_persist(self)': '    if kind in ("BOOT", "FAIL"):\n        _debug_persist(self)',
}
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
    elif new not in text:
        raise SystemExit(f"runtime patch anchor missing: {old[:80]}")

# Keep PLAN|2 header-only routes and nested count/time loops on the small
# executor. Importing the 57 KiB plan_engine for BEEP/DELAY loops exhausts the
# RP2040 heap, while these commands need no mouse/keyboard modules.
text, set_count = re.subn(
    r'_LIGHT_ROUTE_COMMANDS = \{[^\n]+\}',
    '_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP"}',
    text,
    count=1,
)
if set_count != 1:
    raise SystemExit("runtime patch anchor missing: _LIGHT_ROUTE_COMMANDS")

safe_persist = '''def _debug_persist(self):
    # Live tracing belongs to GuardTraceCollector. Never remount or rewrite
    # CIRCUITPY on GP4/STATE/ROUTE events; keep only BOOT/FAIL breadcrumbs in NVM.
    try:
        payload = _debug_trim(_debug_nvm_read() + "".join(self.debug_events))
        ok = _debug_nvm_write(payload)
        if ok:
            self.debug_events = []
        return ok
    except Exception:
        return False

'''
if "Live tracing belongs to GuardTraceCollector" not in text:
    text, count = re.subn(r'def _debug_persist\(self\):\n.*?(?=def _debug_event\(self,)', safe_persist, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("runtime patch anchor missing: _debug_persist")

light_runner = '''def _light_gate(ctx, expected_state):
    owner = ctx.r
    # A route can run for minutes, so it must continue servicing USB, buttons,
    # UART and Guard classification instead of blocking the outer loop.
    owner.host_poll()
    owner.buttons()
    owner.arm.pump()
    while owner.controls.paused and owner.controls.running:
        owner.host_poll()
        owner.buttons()
        owner.arm.pump()
        runtime.time.sleep(.01)
    if not owner.controls.running or owner.calibrating:
        return False
    now = runtime.time.monotonic()
    due = getattr(ctx, "_light_poll_due", 0)
    if now >= due:
        ctx._light_poll_due = now + .25
        active = owner.guard.update(owner.sensor.lux(), int(now * 1000))
        if active != expected_state:
            return False
    return True


def _light_sleep(ctx, milliseconds, expected_state):
    end = runtime.time.monotonic() + max(0, milliseconds) / 1000
    while runtime.time.monotonic() < end:
        if not _light_gate(ctx, expected_state):
            return False
        runtime.time.sleep(.005)
    return True


def _run_light_route(ctx, commands):
    links = {}
    opens = []
    for index, item in enumerate(commands):
        command = item[0]
        if command in ("LOOP", "LOOPTIME"):
            opens.append(index)
        elif command == "ENDLOOP":
            if not opens:
                raise ValueError("ENDLOOP without LOOP")
            start = opens.pop()
            links[start] = index
            links[index] = start
    if opens:
        raise ValueError("LOOP without ENDLOOP")

    expected_state = getattr(ctx.r, "debug_last_state", None)
    ctx._light_poll_due = 0
    frames = []
    pc = 0
    while pc < len(commands):
        if not _light_gate(ctx, expected_state):
            return
        command, args = commands[pc]
        if command == "PLAN":
            if args != "2":
                raise ValueError("unsupported PLAN version")
        elif command == "SCREEN":
            fields = args.split(",")
            if len(fields) != 2:
                raise ValueError("SCREEN needs width,height")
            ctx.screen_w, ctx.screen_h = int(fields[0]), int(fields[1])
        elif command == "SPEED":
            fields = args.split(",")
            if len(fields) != 2:
                raise ValueError("SPEED needs min,max")
            ctx.speed_min, ctx.speed_max = int(fields[0]), int(fields[1])
        elif command == "DELAY":
            fields = args.split(",")
            lo = int(fields[0])
            hi = int(fields[1]) if len(fields) > 1 else lo
            delay = lo if hi <= lo else runtime.random.randint(lo, hi)
            if not _light_sleep(ctx, delay, expected_state):
                return
        elif command == "BEEP":
            fields = args.split(",")
            if len(fields) != 2:
                raise ValueError("BEEP needs frequency,duration")
            ctx.beep(int(fields[0]), int(float(fields[1])))
        elif command == "LOOP":
            count = int(args or "1")
            if count < 0:
                raise ValueError("LOOP count must be non-negative")
            frames.append([pc, links[pc], "count", count])
        elif command == "LOOPTIME":
            seconds = float(args or "0")
            if seconds <= 0:
                raise ValueError("LOOPTIME seconds must be positive")
            frames.append([pc, links[pc], "time", runtime.time.monotonic() + seconds])
        elif command == "ENDLOOP":
            if not frames or frames[-1][0] != links[pc]:
                raise ValueError("invalid loop stack")
            frame = frames[-1]
            if frame[2] == "time":
                if runtime.time.monotonic() < frame[3]:
                    pc = frame[0] + 1
                    continue
                frames.pop()
            elif frame[3] == 0:
                pc = frame[0] + 1
                continue
            else:
                frame[3] -= 1
                if frame[3] > 0:
                    pc = frame[0] + 1
                    continue
                frames.pop()
        pc += 1

'''
text, runner_count = re.subn(
    r'def _run_light_route\(ctx, commands\):\n.*?(?=def _diagnostic_route\(self, decision\):)',
    light_runner,
    text,
    count=1,
    flags=re.S,
)
if runner_count != 1:
    raise SystemExit("runtime patch anchor missing: _run_light_route")

required = (
    '_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP"}',
    'def _light_gate(ctx, expected_state):',
    'runtime.PlanContext(self)',
    'runtime.GuardBundleError("unvalidated route")',
)
for marker in required:
    if marker not in text:
        raise SystemExit("runtime patch verification failed: " + marker)

path.write_text(text, encoding="utf-8", newline="\n")
print(f"verified Combined Guard timed-loop runtime: {path}")
