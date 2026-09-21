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
block='''import random as _light_random

_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "KEY", "KDOWN", "KUP"}
_VALID_ROUTE_NAMES = ("desktop_steps.txt", "login_or_dc_steps.txt", "character_dashboard_steps.txt", "entering_game_loading_steps.txt", "game_steps.txt", "targeted_steps.txt", "resumable_steps.txt")


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


def _light_keycode(vk):
    # Windows virtual-key to USB boot-keyboard usage. Keep this branch-only so
    # route execution does not allocate a dictionary on CircuitPython's heap.
    if 65 <= vk <= 90: return vk - 61
    if 49 <= vk <= 57: return vk - 19
    if vk == 48: return 39
    if 112 <= vk <= 123: return vk - 54
    if vk == 13: return 40
    if vk == 27: return 41
    if vk == 8: return 42
    if vk == 9: return 43
    if vk == 32: return 44
    if vk == 189: return 45
    if vk == 187: return 46
    if vk == 219: return 47
    if vk == 221: return 48
    if vk == 220: return 49
    if vk == 186: return 51
    if vk == 222: return 52
    if vk == 192: return 53
    if vk == 188: return 54
    if vk == 190: return 55
    if vk == 191: return 56
    if vk == 20: return 57
    if vk == 44: return 70
    if vk == 145: return 71
    if vk == 19: return 72
    if vk == 45: return 73
    if vk == 36: return 74
    if vk == 33: return 75
    if vk == 46: return 76
    if vk == 35: return 77
    if vk == 34: return 78
    if vk == 39: return 79
    if vk == 37: return 80
    if vk == 40: return 81
    if vk == 38: return 82
    if vk == 144: return 83
    if vk == 111: return 84
    if vk == 106: return 85
    if vk == 109: return 86
    if vk == 107: return 87
    if vk == 108: return 88
    if 97 <= vk <= 105: return vk - 8
    if vk == 96: return 98
    if vk == 110: return 99
    if vk in (16, 160): return 225
    if vk == 161: return 229
    if vk in (17, 162): return 224
    if vk == 163: return 228
    if vk in (18, 164): return 226
    if vk == 165: return 230
    if vk == 91: return 227
    if vk == 92: return 231
    raise ValueError("unsupported virtual key: %d" % vk)


def _light_hold_ms(value):
    if not value: return 0
    pair = value.split(",")
    if len(pair) == 1:
        lo = hi = int(pair[0])
    elif len(pair) == 2:
        lo = int(pair[0]); hi = int(pair[1])
    else:
        raise ValueError("bad KEY hold")
    if lo < 0 or hi < 0: raise ValueError("negative KEY hold")
    if hi < lo: lo, hi = hi, lo
    return lo if hi == lo else _light_random.randint(lo, hi)


def _light_key(owner, args, expected_state):
    combo = None; hold = 0
    for field in args.split("|"):
        if field.startswith("combo="):
            if combo is not None: raise ValueError("duplicate KEY combo")
            combo = field[6:]
        elif field.startswith("hold="):
            hold = _light_hold_ms(field[5:])
        else:
            raise ValueError("bad KEY field")
    if not combo: raise ValueError("KEY needs combo")
    values = combo.split("+")
    if not values or len(values) > 10: raise ValueError("bad KEY combo")
    codes = []
    for value in values:
        codes.append(_light_keycode(int(value)))
    owner.emit("EVT|DEBUG|STEP/KEY keys=%d hold=%d" % (len(codes), hold))
    pressed = 0
    try:
        for code in codes:
            owner.keyboard.press(code); pressed += 1
        if hold and not _light_sleep(owner, hold, expected_state): return False
        return _light_gate(owner, expected_state)
    finally:
        while pressed:
            pressed -= 1
            owner.keyboard.release(codes[pressed])


def _run_light_route(owner, name):
    gc.collect()
    owner.emit("EVT|DEBUG|MEM/route-enter free=%d" % gc.mem_free())
    expected = getattr(owner, "debug_last_state", None)
    owner.light_poll_due = 0
    frames = []
    with open("/" + name, "r") as fh:
        owner.emit("EVT|DEBUG|MEM/route-open free=%d" % gc.mem_free())
        while True:
            if not _light_gate(owner, expected): return False
            raw = fh.readline()
            if not raw:
                if frames: raise ValueError("LOOP without ENDLOOP")
                return True
            line = raw.strip()
            if not line or line.startswith("#"): continue
            split = line.find("|")
            if split < 0:
                op = line.upper(); args = ""
                if op != "ENDLOOP": raise ValueError("invalid route line")
            else:
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
                if not _light_sleep(owner, int(a[0]), expected): return False
            elif op == "BEEP":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad BEEP")
                owner.emit("EVT|DEBUG|STEP/BEEP %s,%s" % (a[0], a[1]))
                if not _light_beep(owner, int(a[0]), int(float(a[1])), expected): return False
            elif op == "KEY":
                if not _light_key(owner, args, expected): return False
            elif op in ("KDOWN", "KUP"):
                code = _light_keycode(int(args))
                if op == "KDOWN": owner.keyboard.press(code)
                else: owner.keyboard.release(code)
                owner.emit("EVT|DEBUG|STEP/%s vk=%s" % (op, args))
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
    if name not in _VALID_ROUTE_NAMES:
        raise runtime.GuardBundleError("unvalidated route")
    try:
        # Propagate Stop/light-gate cancellation so the caller does not log
        # an aborted Route as successfully completed.
        return _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key.
        self.keyboard.release_all()
        self.arm.flush()

runtime.Combined.route = _diagnostic_route
'''
start=s.find('_LIGHT_ROUTE_COMMANDS =')
marker='runtime.Combined.route = _diagnostic_route'
end=s.find(marker,start)
if start<0 or end<0: raise SystemExit('missing light region')
# Include our import on repeat runs so applying this patch stays idempotent.
import_start=s.rfind('import random as _light_random',0,start)
if import_start>=0 and start-import_start<80: start=import_start
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
