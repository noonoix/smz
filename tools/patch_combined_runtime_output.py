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
_audio_old = '    except Exception:\n        self.emit("ERR|CAL|AUDIO")'
_audio_new = '    except Exception as exc:\n        _debug_event(self, "CAL", "audio-failed=%s" % type(exc).__name__, persist=True)\n        self.emit("ERR|CAL|AUDIO")'
if _audio_old in s: s = s.replace(_audio_old, _audio_new, 1)
_audio_cue_old = 'def _guard_start_tone(self):\n    self._guard_pattern(_GUARD_START_PATTERN)'
_audio_cue_new = 'def _guard_start_tone(self):\n    _debug_event(self, "CAL", "start-cue", persist=True)\n    self._guard_pattern(_GUARD_START_PATTERN)'
if _audio_cue_old in s: s = s.replace(_audio_cue_old, _audio_cue_new, 1)
block=r'''import random as _light_random

_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "KEY", "KDOWN", "KUP", "TYPE", "RMOUSE", "MOVETO"}
_VALID_ROUTE_NAMES = ("desktop_steps.txt", "restart_steps.txt", "login_or_dc_steps.txt", "character_dashboard_steps.txt", "entering_game_loading_steps.txt", "game_steps.txt", "targeted_steps.txt", "resumable_steps.txt")


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
        owner.emit("EVT|DEBUG|STEP/KEY press-start")
        for index in range(len(codes)):
            owner.emit("EVT|DEBUG|STEP/KEY press-index=%d code=%d" % (index, codes[index]))
            owner.keyboard.press(codes[index]); pressed += 1
            owner.emit("EVT|DEBUG|STEP/KEY press-ok=%d" % index)
        owner.emit("EVT|DEBUG|STEP/KEY pressed")
        if hold and not _light_sleep(owner, hold, expected_state): return False
        owner.emit("EVT|DEBUG|STEP/KEY release-start")
        while pressed:
            pressed -= 1
            owner.emit("EVT|DEBUG|STEP/KEY release-index=%d code=%d" % (pressed, codes[pressed]))
            owner.keyboard.release(codes[pressed])
        owner.emit("EVT|DEBUG|STEP/KEY released")
        return _light_gate(owner, expected_state)
    finally:
        while pressed:
            pressed -= 1
            try:
                owner.keyboard.release(codes[pressed])
            except Exception as cleanup:
                owner.emit("EVT|DEBUG|STEP/KEY cleanup-failed " + type(cleanup).__name__)


def _light_package_delay(owner, args, expected):
    parts = args.split(",")
    if len(parts) not in (1, 2): raise ValueError("bad DELAY range")
    lo = int(parts[0]); hi = int(parts[-1])
    if lo < 0 or hi < 0: raise ValueError("negative DELAY")
    if hi < lo: lo, hi = hi, lo
    value = lo if hi <= lo else _light_random.randint(lo, hi)
    return _light_sleep(owner, value, expected)


def _light_package_action(owner, op, args, expected):
    if op == "DELAY": return _light_package_delay(owner, args, expected)
    if op == "KEY": return _light_key(owner, args, expected)
    if op == "TYPE": return _light_type(owner, args, expected)
    if op in ("RMOUSE", "MOVETO"): return _light_mouse(owner, op, args, expected)
    if op in ("KDOWN", "KUP"):
        code = _light_keycode(int(args))
        if op == "KDOWN": owner.keyboard.press(code)
        else: owner.keyboard.release(code)
        owner.emit("EVT|DEBUG|STEP/%s vk=%s" % (op, args))
        return _light_gate(owner, expected)
    if op == "BEEP":
        fields = args.split(",")
        if len(fields) != 2: raise ValueError("bad BEEP")
        owner.emit("EVT|DEBUG|STEP/BEEP %s,%s" % (fields[0], fields[1]))
        return _light_beep(owner, int(fields[0]), int(float(fields[1])), expected)
    raise ValueError("unsupported package command: " + op)
def _type_pair(value, default_lo=0, default_hi=0):
    if value is None: return default_lo, default_hi
    a=value.split(",")
    if len(a)!=2: raise ValueError("bad TYPE range")
    lo=int(a[0]); hi=int(a[1])
    if lo<0 or hi<0: raise ValueError("negative TYPE range")
    if hi<lo: lo,hi=hi,lo
    return lo,hi


def _type_roll(pair):
    return pair[0] if pair[1]<=pair[0] else _light_random.randint(pair[0],pair[1])


def _type_decode(value):
    out=[]; i=0
    while i<len(value):
        if value[i]=="%" and i+2<len(value):
            try:
                out.append(chr(int(value[i+1:i+3],16))); i+=3; continue
            except Exception: pass
        out.append(value[i]); i+=1
    return "".join(out)


def _type_key(ch):
    o=ord(ch)
    if 97<=o<=122: return o-93,False
    if 65<=o<=90: return o-61,True
    if 49<=o<=57: return o-19,False
    if ch=="0": return 39,False
    if ch==" ": return 44,False
    if ch=="\t": return 43,False
    if ord(ch)==8: return 42,False
    if ch in "\r\n": return 40,False
    plain="-=[]\\;'`,./"
    shifted="_+{}|:\"~<>?"
    i=plain.find(ch)
    if i>=0:
        return (45,46,47,48,49,51,52,53,54,55,56)[i],False
    i=shifted.find(ch)
    if i>=0:
        return (45,46,47,48,49,51,52,53,54,55,56)[i],True
    symbols="!@#$%^&*()"
    i=symbols.find(ch)
    if i>=0: return (30,31,32,33,34,35,36,37,38,39)[i],True
    raise ValueError("TYPE supports exported ASCII text only")


def _type_char(owner,ch,hold,expected):
    code,shift=_type_key(ch); down=0
    try:
        if shift: owner.keyboard.press(225); down=1
        owner.keyboard.press(code); down=2
        if not _light_sleep(owner,_type_roll(hold),expected): return False
        owner.keyboard.release(code); down=1 if shift else 0
        if shift: owner.keyboard.release(225); down=0
        return _light_gate(owner,expected)
    finally:
        if down>=2:
            try: owner.keyboard.release(code)
            except Exception: pass
        if down>=1 and shift:
            try: owner.keyboard.release(225)
            except Exception: pass


def _type_neighbor(ch):
    low=ch.lower()
    for row in ("1234567890","qwertyuiop","asdfghjkl","zxcvbnm"):
        i=row.find(low)
        if i>=0:
            j=i+(-1 if _light_random.randrange(2)==0 else 1)
            if j<0 or j>=len(row): j=1 if i==0 else i-1
            n=row[j]
            return n.upper() if ch.isupper() else n
    return None


def _light_type(owner,args,expected):
    vals={}
    for field in args.split("|"):
        if "=" not in field: raise ValueError("bad TYPE field")
        k,v=field.split("=",1); vals[k]=v
    if "text" not in vals: raise ValueError("TYPE needs text")
    text=_type_decode(vals["text"])
    hold=_type_pair(vals.get("h"),80,220)
    word=_type_pair(vals.get("w"),0,0)
    punct=_type_pair(vals.get("p"),0,0)
    typo=_type_pair(vals.get("typo"),0,0)
    wp=max(0,min(100,int(vals.get("wp","100"))))
    think_chance=0; think=(800,2200)
    if "think" in vals:
        a=vals["think"].split(":",1)
        if len(a)!=2: raise ValueError("bad TYPE think")
        think_chance=max(0,min(100,int(a[0]))); think=_type_pair(a[1])
    typo_on=typo[1]>0
    next_typo=max(1,_type_roll(typo)) if typo_on else -1
    chars_since_typo=0; i=0
    owner.emit("EVT|DEBUG|STEP/TYPE chars=%d typo=%s" % (len(text), "on" if typo_on else "off"))
    while i<len(text):
        ch=text[i]
        if typo_on and not ch.isspace() and chars_since_typo>=next_typo:
            wrong=_type_neighbor(ch)
            if wrong is not None:
                if not _type_char(owner,wrong,hold,expected): return False
                if not _light_sleep(owner,_light_random.randint(max(hold[1],120),hold[1]*2+200),expected): return False
                if not _type_char(owner,chr(8),hold,expected): return False
                if not _light_sleep(owner,_type_roll(hold),expected): return False
                owner.emit("EVT|DEBUG|STEP/TYPE typo-correction char=%d" % i)
                chars_since_typo=0
                next_typo=max(1,_type_roll(typo))
        if not _type_char(owner,ch,hold,expected): return False
        chars_since_typo += 1
        if ch in ".,!?;:" and punct[1]>0:
            if not _light_sleep(owner,_type_roll(punct),expected): return False
        if ch.isspace():
            if word[1]>0 and _light_random.randrange(100)<wp:
                if not _light_sleep(owner,_type_roll(word),expected): return False
            if think_chance>0 and think[1]>0 and _light_random.randrange(100)<think_chance:
                if not _light_sleep(owner,_type_roll(think),expected): return False
        i+=1
    return True

def _mouse_pair(value, default):
    if value is None: return default
    a=value.split(",")
    if len(a)!=2: raise ValueError("bad mouse range")
    lo=int(a[0]); hi=int(a[1])
    if lo<0 or hi<0 or hi<lo: raise ValueError("invalid mouse range")
    return lo,hi


def _arm_send_cooperative(owner, line, timeout=5):
    # Mouse/HID calls must continue servicing GP4/GP3, host commands and UART
    # while the Pro Micro is acknowledging a human-mouse command.
    owner.arm.pump()
    owner.arm.write(line)
    head = line.split("|", 1)[0]
    # The ARM 2.7 firmware executes HRANDOM through hm3_move() and
    # acknowledges it as OK|HMOVE. Accept that canonical semantic reply.
    ack_head = "HMOVE" if head == "HRANDOM" else head
    end = runtime.time.monotonic() + timeout
    while runtime.time.monotonic() < end:
        owner.host_poll()
        owner.buttons()
        for reply in owner.arm.pump():
            if reply.startswith("OK|" + ack_head) or reply.startswith("ERR|"):
                return reply
        if not owner.controls.running and not owner.calibrating:
            return "ERR|STOPPED"
        runtime.time.sleep(.002)
    raise RuntimeError("arm acknowledgement timeout: " + head)


def _mouse_profile(owner, values):
    cap=_arm_send_cooperative(owner,"HVER",3)
    if not cap.startswith("OK|HVER|2.7.0|HMOUSE=1"):
        raise RuntimeError("ARM 2.7 human mouse capability required")
    speed=getattr(owner,"route_speed",(150,500))
    mt=_mouse_pair(values.get("mt"),(0,0))
    curve=_mouse_pair(values.get("curve"),(15,45))
    before=_mouse_pair(values.get("before"),(120,450))
    after=_mouse_pair(values.get("after"),(150,600))
    mid=(12,100,400)
    if "mid" in values:
        a=values["mid"].split(":",1)
        if len(a)!=2: raise ValueError("bad mouse mid")
        r=_mouse_pair(a[1],(100,400)); mid=(int(a[0]),r[0],r[1])
    idle=(5,12,800,3000)
    if "idle" in values:
        a=values["idle"].split(":",1)
        if len(a)!=2: raise ValueError("bad mouse idle")
        every=_mouse_pair(a[0],(5,12)); pause=_mouse_pair(a[1],(800,3000))
        idle=(every[0],every[1],pause[0],pause[1])
    over=int(values.get("over","15"))
    if not 0<=mid[0]<=100 or not 0<=over<=100: raise ValueError("mouse chance out of range")
    cfg="HCFG|%d,%d,%d,%d,%d,%d,%d,%d,%d,%d"%(speed[0],speed[1],mt[0],mt[1],curve[0],curve[1],before[0],before[1],after[0],after[1])
    pauses="HPAUSE|%d,%d,%d,%d,%d,%d,%d,%d"%(mid[0],mid[1],mid[2],idle[0],idle[1],idle[2],idle[3],over)
    if not _arm_send_cooperative(owner,cfg,3).startswith("OK|"): raise RuntimeError("ARM HCFG rejected")
    if not _arm_send_cooperative(owner,pauses,3).startswith("OK|"): raise RuntimeError("ARM HPAUSE rejected")


def _mouse_values(args):
    values={}
    for field in args.split("|"):
        if "=" not in field: raise ValueError("bad mouse field")
        k,v=field.split("=",1)
        if k in values: raise ValueError("duplicate mouse field")
        values[k]=v
    return values


def _light_mouse(owner,op,args,expected):
    values=_mouse_values(args)
    if not _light_gate(owner,expected): return False
    if op=="MOVETO":
        if "x" not in values or "y" not in values: raise ValueError("MOVETO needs x/y")
        x=int(values["x"]); y=int(values["y"]); human=int(values.get("human","1"))
        if human==0:
            reply=_arm_send_cooperative(owner,"MMOVE|%d,%d,abs,0"%(x,y),8)
        else:
            _mouse_profile(owner,values); reply=_arm_send_cooperative(owner,"HMOVE|%d,%d"%(x,y),35)
    else:
        if "region" not in values: raise ValueError("RMOUSE needs region")
        a=values["region"].split(",")
        if len(a)!=4: raise ValueError("bad RMOUSE region")
        x,y,w,h=(int(v) for v in a)
        if w<1 or h<1: raise ValueError("bad RMOUSE region")
        _mouse_profile(owner,values); reply=_arm_send_cooperative(owner,"HRANDOM|%d,%d,%d,%d"%(x,y,w,h),35)
    if reply == "ERR|STOPPED": return False
    if not reply.startswith("OK|"):
        owner.emit("EVT|DEBUG|ARM/%s reply=%s"%(op,reply))
        raise RuntimeError("ARM human mouse rejected: " + reply)
    owner.emit("EVT|DEBUG|STEP/%s arm27=ok"%op)
    return _light_gate(owner,expected)

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
                w=int(a[0]); h=int(a[1])
                if w<1 or h<1: raise ValueError("bad SCREEN")
                owner.route_screen=(w,h)
                if not owner.arm.send("SETRES|%d,%d"%(w,h),3).startswith("OK|"): raise RuntimeError("ARM SETRES rejected")
            elif op == "SPEED":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SPEED")
                lo=int(a[0]); hi=int(a[1])
                if lo<0 or hi<lo: raise ValueError("bad SPEED")
                owner.route_speed=(lo,hi)
            elif op == "DELAY":
                if not _light_package_delay(owner, args, expected): return False
            elif op == "RPKG":
                from random_package_runtime import run_file_package
                if not run_file_package(fh, args, owner, expected, _light_package_action): return False
            elif op == "BEEP":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad BEEP")
                owner.emit("EVT|DEBUG|STEP/BEEP %s,%s" % (a[0], a[1]))
                if not _light_beep(owner, int(a[0]), int(float(a[1])), expected): return False
            elif op == "KEY":
                if not _light_key(owner, args, expected): return
            elif op == "TYPE":
                if not _light_type(owner, args, expected): return
            elif op in ("RMOUSE", "MOVETO"):
                if not _light_mouse(owner, op, args, expected): return
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


_RESTART_MARKER = "/.combined_restart_pending"

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

def _diagnostic_route(self, decision):
    if not decision.get("execute"):
        return False
    name = decision.get("route")
    if name not in _VALID_ROUTE_NAMES:
        raise runtime.GuardBundleError("unvalidated route")
    primary = None
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
        return _run_light_route(self, name)
    except Exception as exc:
        primary = exc
        raise
    finally:
        try:
            self.keyboard.release_all()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/keyboard " + type(cleanup).__name__)
            if primary is None: raise
        try:
            self.arm.release(False)
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/mouse " + type(cleanup).__name__)
        try:
            self.arm.release(False)
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/mouse " + type(cleanup).__name__)
        try:
            self.arm.flush()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/arm " + type(cleanup).__name__)
            if primary is None: raise

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
required = (
    'def _cal_beep(self, frequency, duration_ms):',
    '_GUARD_START_PATTERN',
    'runtime.Combined.guard_start_tone = _guard_start_tone',
    'runtime.board.GP6',
    'def _light_package_delay(owner, args, expected):',
    'def _light_package_action(owner, op, args, expected):',
    'elif op == \"RPKG\":',
    'run_file_package',
    'elif op == \"TYPE\":',
    'elif op in (\"RMOUSE\", \"MOVETO\"):',
    'elif op in (\"LOOP\", \"LOOPTIME\"):',
    'elif op == \"ENDLOOP\":',
)
missing = [token for token in required if token not in s]
if missing:
    raise SystemExit('combined runtime contract missing: ' + ', '.join(missing))
p.write_text(s,encoding='utf-8',newline='\n')
print('patched',p)
print('patched',p)
