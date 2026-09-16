# Combined Phase 7 board-owned runtime. It validates the exported bundle before routing.
import json
import math
import os
import time
import board
import busio
import digitalio
import pwmio
import usb_cdc
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import plan_engine
from live_light_guard import GuardBundleError, LightStateGuard, load_guard_bundle

PROFILES = ("desktop", "login-or-dc", "character-dashboard", "entering-game-loading", "game", "targeted")

class BH1750:
    def __init__(self):
        self.i2c = busio.I2C(board.GP21, board.GP20); self.buf = bytearray(2)
        for command in (1, 7, 0x10): self._write(command)
        time.sleep(.2)
    def _write(self, command):
        while not self.i2c.try_lock(): pass
        try: self.i2c.writeto(0x23, bytes((command,)))
        finally: self.i2c.unlock()
    def lux(self):
        while not self.i2c.try_lock(): pass
        try: self.i2c.readfrom_into(0x23, self.buf)
        finally: self.i2c.unlock()
        value = ((self.buf[0] << 8) | self.buf[1]) / 1.2
        if not math.isfinite(value) or value < 0: raise RuntimeError("invalid lux")
        return value

class Arm:
    """UART0 GP16/GP17 transport: checksum frames, short-write rejection, two-move back-pressure."""
    def __init__(self):
        self.uart = busio.UART(board.GP16, board.GP17, baudrate=57600, timeout=.05)
        self.buf = bytearray(); self.pending = 0; self.held = set()
    def frame(self, line): return ("#%02X|%s\n" % (sum(line.encode()) & 255, line)).encode()
    def write(self, line):
        data = self.frame(line); count = self.uart.write(data)
        if count is not None and count != len(data): raise RuntimeError("short UART write")
    def pump(self):
        if self.uart.in_waiting: self.buf.extend(self.uart.read(self.uart.in_waiting))
        replies = []
        while b"\n" in self.buf:
            raw, self.buf = self.buf.split(b"\n", 1); line = raw.decode("utf-8", "replace").strip()
            if line.startswith("OK|MMOVE"): self.pending = max(0, self.pending - 1)
            elif line.startswith("EVT|"): print(line)
            elif line: replies.append(line)
        return replies
    def move(self, x, y):
        end = time.monotonic() + 2
        while self.pending >= 2:
            self.pump()
            if time.monotonic() > end: raise RuntimeError("arm back-pressure timeout")
            time.sleep(.001)
        self.write("MMOVE|%d,%d,abs,2" % (x, y)); self.pending += 1
    def send(self, line, timeout=5):
        self.pump(); self.write(line); head = line.split("|", 1)[0]; end = time.monotonic() + timeout
        while time.monotonic() < end:
            for reply in self.pump():
                if reply.startswith("OK|" + head) or reply.startswith("ERR|"): return reply
            time.sleep(.002)
        raise RuntimeError("arm acknowledgement timeout: " + head)
    def flush(self):
        end = time.monotonic() + 3
        while self.pending and time.monotonic() < end: self.pump(); time.sleep(.002)
        if self.pending: raise RuntimeError("arm move acknowledgement timeout")
    def release(self, force=True):
        for button in (("left", "right", "middle") if force else tuple(self.held)):
            try: self.send("MUP|" + button, 1)
            except Exception: pass
        self.held.clear(); self.pending = 0
    def abort(self):
        try: self.send("HALT", 1.5)
        except Exception: pass
        self.release(True)

class Button:
    def __init__(self, pin):
        self.io = digitalio.DigitalInOut(pin); self.io.direction = digitalio.Direction.INPUT; self.io.pull = digitalio.Pull.UP
        self.down = False; self.changed = 0; self.started = 0; self.long = False
    def poll(self, now):
        pressed = not self.io.value
        if pressed != self.down and now - self.changed >= .04:
            self.changed = now; self.down = pressed
            if pressed: self.started = now; self.long = False; return "down"
            return "up"
        if pressed and not self.long and now - self.started >= 3: self.long = True; return "long"
        return None

class Controls:
    def __init__(self, arm): self.arm = arm; self.running = False; self.paused = False; self.aborted = False
    def start(self): self.running = True; self.paused = False; self.aborted = False
    def stop(self): self.running = False; self.paused = False; self.aborted = True; self.arm.abort()
    def gate(self):
        while self.paused and self.running: self.arm.pump(); time.sleep(.01)
        return self.running and not self.aborted
    def sleep(self, milliseconds):
        end = time.monotonic() + max(0, milliseconds) / 1000
        while time.monotonic() < end:
            self.arm.pump()
            if not self.gate(): return False
            time.sleep(.005)
        return True

class PlanContext:
    plan_api = 3; screen_w = 1920; screen_h = 1080; speed_min = 0; speed_max = 2000
    def __init__(self, runtime): self.r = runtime
    def now(self): return time.monotonic()
    def gate(self): return self.r.controls.gate()
    def sleep_ms(self, ms): return self.r.controls.sleep(ms)
    def log(self, text): print("plan:", text)
    def mmove(self, x, y): self.r.arm.move(x, y)
    def mclick(self, button, count, hmin, hmax): self.r.arm.send("MCLICK|%s,%d,%d,%d" % (button, count, hmin, hmax), 8)
    def ktext(self, hmin, hmax, text): self.r.type_text(text, hmin, hmax, self)
    def kcombo(self, value): self.key_combo([value], 0, 0)
    def key(self, vk, hold): self.key_combo([vk], hold, hold)
    def key_combo(self, vks, hmin, hmax):
        codes = [self.r.key(v) for v in vks]
        for code in codes: self.r.keyboard.press(code)
        self.sleep_ms(max(hmin, hmax))
        for code in reversed(codes): self.r.keyboard.release(code)
    def kdown(self, vk): self.r.keyboard.press(self.r.key(vk))
    def kup(self, vk): self.r.keyboard.release(self.r.key(vk))
    def wheel(self, delta): self.r.arm.send("MWHEEL|%d" % delta, 3)
    def raw(self, line): return self.r.arm.send(str(line), 5)
    def setres(self, w, h): return self.r.arm.send("SETRES|%d,%d" % (w, h), 5)
    def wait_sound(self, threshold, minimum, timeout):
        reply = self.r.arm.send("WSND|%d,%d,%d" % (threshold, minimum, timeout), timeout / 1000 + 3)
        return True if "DETECTED" in reply else False if "TIMEOUT" in reply else None
    def trg_sound(self, threshold, minimum, timeout, action, rmin, rmax, hmin, hmax):
        return self.r.arm.send("TRGSND|%d,%d,%d,%d,%d,%d,%d,%d" % (threshold, minimum, timeout, action, rmin, rmax, hmin, hmax), timeout / 1000 + 3).startswith("OK|")
    def beep(self, frequency, duration):
        tone = pwmio.PWMOut(board.GP6, duty_cycle=32768, frequency=int(frequency), variable_frequency=True)
        try: self.sleep_ms(duration)
        finally: tone.duty_cycle = 0; tone.deinit()
    def read_plan_file(self, name):
        if not name or any(c in name for c in "/\\:"): raise ValueError("unsafe include")
        with open("/" + name, "r") as fh: return fh.read()
    def wait_light(self, lo, hi, stable, timeout, mode):
        start = None; end = time.monotonic() + timeout / 1000
        while time.monotonic() < end:
            value = self.r.sensor.lux()
            if lo <= value <= hi:
                if start is None: start = time.monotonic()
                if (time.monotonic() - start) * 1000 >= stable: return True
            else: start = None
            if not self.sleep_ms(20): return False
        return False

class Combined:
    def __init__(self):
        self.arm = Arm(); self.controls = Controls(self.arm); self.keyboard = Keyboard(usb_hid.devices); self.sensor = BH1750()
        self.bundle = load_guard_bundle("/"); self.guard = LightStateGuard.from_bundle("/"); self.routes = {}
        self.blue = Button(board.GP4); self.yellow = Button(board.GP3); self.usb = usb_cdc.data or usb_cdc.console; self.host = bytearray()
        self.calibrating = False; self.stage = 0; self.samples = []; self.sample_started = 0; self.result = None; self.saved = False; self.saved_ids = set()
    def key(self, vk):
        if 65 <= vk <= 90: return getattr(Keycode, chr(vk))
        if 48 <= vk <= 57: return getattr(Keycode, ("ZERO","ONE","TWO","THREE","FOUR","FIVE","SIX","SEVEN","EIGHT","NINE")[vk-48])
        if 112 <= vk <= 123: return getattr(Keycode, "F" + str(vk - 111))
        return {13:Keycode.ENTER, 27:Keycode.ESCAPE, 32:Keycode.SPACE, 9:Keycode.TAB, 8:Keycode.BACKSPACE, 37:Keycode.LEFT_ARROW,38:Keycode.UP_ARROW,39:Keycode.RIGHT_ARROW,40:Keycode.DOWN_ARROW,160:Keycode.LEFT_SHIFT,162:Keycode.LEFT_CONTROL,164:Keycode.LEFT_ALT,91:Keycode.LEFT_GUI}.get(vk, Keycode.E)
    def type_text(self, text, hmin, hmax, ctx):
        for ch in text:
            if not ctx.gate(): raise plan_engine.PlanAbort()
            code = self.key(ord(ch.upper())) if ch.isalnum() else self.key(32 if ch == " " else 13)
            self.keyboard.press(code); self.keyboard.release(code)
            if not ctx.sleep_ms(hmax if hmax > hmin else hmin): raise plan_engine.PlanAbort()
    def emit(self, line):
        try: self.usb.write((line + "\n").encode())
        except Exception: pass
    def start_cal(self):
        self.controls.stop(); self.calibrating = True; self.stage = 0; self.samples = []; self.result = None; self.saved = False; self.saved_ids = set(); self.emit("EVT|CAL|mode=ready|stage=1|id=" + PROFILES[0] + "|seconds=5|saved=0")
    def end_cal(self):
        if self.result is not None and not self.saved: self.emit("ERR|CAL|UNSAVED|stage=%d" % (self.stage + 1)); return
        self.calibrating = False; self.result = None; self.emit("EVT|CAL|mode=exited|saved=%d" % len(self.saved_ids))
    def save_cal(self):
        try:
            with open("/guard-calibration.json", "r") as fh: payload = json.load(fh)
        except Exception: payload = {"format":1,"revision":"","profiles":{}}
        payload.setdefault("profiles", {})[PROFILES[self.stage]] = self.result; payload["revision"] = ""; temp = "/guard-calibration.json.tmp"
        with open(temp, "w") as fh: json.dump(payload, fh)
        try: os.remove("/guard-calibration.json")
        except Exception: pass
        os.rename(temp, "/guard-calibration.json"); self.saved = True; self.saved_ids.add(PROFILES[self.stage]); self.emit("EVT|CAL|mode=saved-stage|stage=%d|id=%s|saved=%d" % (self.stage+1, PROFILES[self.stage], len(self.saved_ids)))
    def yellow_action(self):
        if not self.calibrating: self.controls.paused = not self.controls.paused; return
        if self.result is not None: self.save_cal(); return
        self.samples = []; self.sample_started = time.monotonic(); self.result = "sampling"; self.emit("EVT|CAL|mode=started|stage=%d|id=%s|seconds=5|saved=%d" % (self.stage+1, PROFILES[self.stage], len(self.saved_ids)))
    def cal_tick(self):
        if not self.calibrating or self.result != "sampling": return
        self.samples.append(self.sensor.lux())
        if time.monotonic() - self.sample_started < 5: return
        values = sorted(self.samples); center = values[len(values)//2]; spread = max(values)-min(values)
        if len(values) < 5 or spread > 5: self.result = None; self.emit("ERR|CAL|UNSTABLE|stage=%d|spread=%.1f" % (self.stage+1, spread)); return
        self.result = {"center":center,"tolerance":max(2.0,spread*1.5),"stable_ms":750}; self.saved = False; self.emit("EVT|CAL|mode=complete-stage|stage=%d|id=%s|center=%.1f|spread=%.1f|tolerance=%.1f|saved=0" % (self.stage+1, PROFILES[self.stage], center, spread, self.result["tolerance"]))
    def next_cal(self):
        if not self.calibrating: return
        if self.result is not None and not self.saved: self.emit("ERR|CAL|UNSAVED|stage=%d" % (self.stage+1)); return
        if self.stage >= 5: self.emit("EVT|CAL|mode=last|stage=6|saved=%d" % len(self.saved_ids)); return
        self.stage += 1; self.result = None; self.saved = False; self.emit("EVT|CAL|mode=ready|stage=%d|id=%s|seconds=5|saved=%d" % (self.stage+1, PROFILES[self.stage], len(self.saved_ids)))
    def buttons(self):
        now = time.monotonic(); blue = self.blue.poll(now); yellow = self.yellow.poll(now)
        if blue == "long": self.end_cal() if self.calibrating else self.start_cal()
        elif blue == "up" and not self.blue.long: self.next_cal() if self.calibrating else (self.controls.stop() if self.controls.running else (self.guard.reset(), self.controls.start()))
        if yellow == "up" and not self.yellow.long: self.yellow_action()
        self.cal_tick()
    def route(self, decision):
        if not decision.get("execute"): return
        name = decision.get("route")
        if name not in self.bundle["manifest"]["routes"].values(): raise GuardBundleError("unvalidated route")
        if name not in self.routes:
            with open("/" + name, "r") as fh: self.routes[name] = plan_engine.parse_plan(fh.read())
        plan_engine.run_plan(self.routes[name], PlanContext(self)); self.arm.flush()
    def host_poll(self):
        if self.usb.in_waiting: self.host.extend(self.usb.read(self.usb.in_waiting))
        while b"\n" in self.host:
            raw, self.host = self.host.split(b"\n", 1); line = raw.decode("utf-8", "replace").strip()
            if not line: continue
            try:
                if line == "PING": reply = "OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6"
                elif line == "GUARD|ON": self.controls.start(); reply = "OK|GUARD|ON"
                elif line in ("GUARD|OFF", "HALT"): self.controls.stop(); reply = "OK|GUARD|OFF"
                elif line == "LUX?": reply = "OK|LUX|lux=%.1f|sensor=ok" % self.sensor.lux()
                else: reply = "ERR|GUARD|UNKNOWN"
                self.emit(reply)
            except Exception: self.emit("ERR|EXC")
    def loop(self):
        self.emit("combined-pico-guard-executor|GP4 start/stop hold3s=calibration|GP3 pause/resume|GP6 piezo"); last = 0
        while True:
            self.host_poll(); self.buttons(); self.arm.pump()
            if self.controls.running and not self.calibrating and time.monotonic() - last >= .25:
                last = time.monotonic()
                try:
                    self.guard.update(self.sensor.lux(), int(last * 1000))
                    if self.guard.last_decision is not None: self.route(self.guard.last_decision)
                except Exception as exc: self.controls.stop(); self.emit("ERR|GUARD|FAIL|" + str(exc)[:60])
            time.sleep(.01)

def main():
    try: Combined().loop()
    except GuardBundleError as exc: print("combined Guard bundle rejected:", exc)
    except Exception as exc: print("combined Guard stopped:", exc)
