# sim60diag.py - fake-hardware simulation of code60a-diag.py (golden rule 3: simulate first).
# Stubs CircuitPython modules, execs the filled diag firmware, captures stdout for DIAG lines.
# ASCII output only. (v2: Keycode stub completed - arrow keys + digit names the firmware needs.)
import contextlib
import io
import sys
import types

SRC = open("/data/code60a-diag.py", encoding="utf-8").read()
compile(SRC, "code60a-diag.py", "exec")
print("PASS: diag firmware compiles")

results = []
def check(cond, msg):
    results.append((bool(cond), msg))
    print(("PASS: " if cond else "FAIL: ") + msg)

class SimExit(BaseException):
    pass

def run_scenario(name, sensor_ok=True, arm_ok=True, feed=b"", calib=None,
                 sleep_limit=3000, btn_script=None):
    clock = [100.0]
    sleeps = [0]

    t = types.ModuleType("time")
    t.monotonic = lambda: clock[0]
    def _sleep(s):
        clock[0] += s
        sleeps[0] += 1
        if btn_script:
            btn_script(sleeps[0], btns)
        if sleeps[0] > sleep_limit:
            raise SimExit()
    t.sleep = _sleep

    board = types.ModuleType("board")
    for p in ("GP21", "GP20", "GP16", "GP17", "GP4", "GP3"):
        setattr(board, p, p)

    class FakeI2C:
        def __init__(self, *a):
            if not sensor_ok:
                raise OSError("no sensor")
        def try_lock(self):
            return True
        def unlock(self):
            pass
        def writeto(self, addr, b):
            pass
        def readfrom_into(self, addr, buf):
            raw = int(1200.0 * 1.2)
            buf[0] = (raw >> 8) & 0xFF
            buf[1] = raw & 0xFF

    class FakeUART:
        def __init__(self, *a, **k):
            if not arm_ok:
                raise OSError("no arm")
            self.written = []
            self._sched = []
        @property
        def in_waiting(self):
            return sum(len(b) for at, b in self._sched if at <= clock[0])
        def read(self, n=None):
            outb = b""
            keep = []
            for at, b in self._sched:
                if at <= clock[0]:
                    outb += b
                else:
                    keep.append((at, b))
            self._sched = keep
            return outb
        def write(self, b):
            line = b.decode().strip()
            self.written.append(line)
            if line in ("HALT", "BYE"):
                self._sched.append((clock[0] + 0.01, ("OK|" + line + "\n").encode()))
            return len(b)

    busio = types.ModuleType("busio")
    busio.I2C = FakeI2C
    busio.UART = FakeUART

    class FakeSerial:
        def __init__(self):
            self._in = bytearray(feed)
            self.lines = []
        @property
        def in_waiting(self):
            return min(3, len(self._in))      # drip-feed: 3 bytes per poll
        def read(self, n):
            n = min(n or 0, len(self._in))
            outb = bytes(self._in[:n])
            del self._in[:n]
            return outb
        def write(self, b):
            self.lines.append(b.decode().strip())
            return len(b)

    serial_obj = FakeSerial()
    usb_cdc = types.ModuleType("usb_cdc")
    usb_cdc.data = serial_obj
    usb_cdc.console = types.SimpleNamespace(connected=True)   # pico_console attached
    usb_hid = types.ModuleType("usb_hid")
    usb_hid.devices = []

    kbd_log = {"press": [], "release": [], "write": []}
    class FakeKeyboard:
        def __init__(self, devices):
            pass
        def press(self, code):
            kbd_log["press"].append(code)
        def release(self, code):
            kbd_log["release"].append(code)
        def write(self, ch):
            kbd_log["write"].append(ch)

    # FULL Keycode stub: every attribute the firmware touches at import or runtime.
    kc = types.SimpleNamespace()
    for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        setattr(kc, ch, 1000 + i)
    for i, nm in enumerate(("ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")):
        setattr(kc, nm, 1100 + i)
    for i in range(1, 25):
        setattr(kc, "F" + str(i), 1200 + i)
    kc.ENTER = 13; kc.ESCAPE = 27; kc.SPACE = 32; kc.TAB = 9; kc.BACKSPACE = 8
    kc.LEFT_ARROW = 37; kc.RIGHT_ARROW = 39; kc.UP_ARROW = 38; kc.DOWN_ARROW = 40
    kc.LEFT_SHIFT = 160; kc.RIGHT_SHIFT = 161; kc.LEFT_CONTROL = 162; kc.RIGHT_CONTROL = 163
    kc.LEFT_ALT = 164; kc.RIGHT_ALT = 165; kc.LEFT_GUI = 91; kc.RIGHT_GUI = 92
    kc.E = 1000 + ord("E") - ord("A")
    kc.KEYPAD_NUMLOCK = 2001
    kc.SCROLL_LOCK = 2002

    ah = types.ModuleType("adafruit_hid")
    ah_kbd = types.ModuleType("adafruit_hid.keyboard")
    ah_kbd.Keyboard = FakeKeyboard
    ah_kc = types.ModuleType("adafruit_hid.keycode")
    ah_kc.Keycode = kc

    class FakeBtn:
        def __init__(self, pin):
            self.pin = pin
            self.value = True
            self.direction = None
            self.pull = None
    btns = {"GP4": FakeBtn("GP4"), "GP3": FakeBtn("GP3")}
    dio = types.ModuleType("digitalio")
    dio.DigitalInOut = lambda pin: btns[pin]
    dio.Direction = types.SimpleNamespace(INPUT="in")
    dio.Pull = types.SimpleNamespace(UP="up")

    def fake_open(path, mode="r"):
        if path == "/pico-calibration.json":
            if calib is None:
                raise OSError("no calibration file")
            import json as _json
            return io.StringIO(_json.dumps(calib))
        raise OSError("unexpected open: " + path)

    saved = {}
    mods = {"time": t, "board": board, "busio": busio, "usb_cdc": usb_cdc,
            "usb_hid": usb_hid, "digitalio": dio,
            "adafruit_hid": ah, "adafruit_hid.keyboard": ah_kbd,
            "adafruit_hid.keycode": ah_kc}
    for m, v in mods.items():
        saved[m] = sys.modules.get(m)
        sys.modules[m] = v
    g = {"__name__": "__main__", "open": fake_open}
    cap = io.StringIO()
    try:
        try:
            with contextlib.redirect_stdout(cap):
                exec(compile(SRC, "code60a-diag.py", "exec"), g)
        except SimExit:
            pass
    finally:
        for m in mods:
            if saved[m] is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = saved[m]
    diag = cap.getvalue()
    print("--- scenario %s: %d fake sleeps, %d PC lines, %d DIAG chars" %
          (name, sleeps[0], len(serial_obj.lines), len(diag)))
    return g, serial_obj, kbd_log, btns, diag


# ---- DIAG-1: full stack, PING + malformed + HALT with DIAG logging ----
g, ser, kbd, btns, diag = run_scenario(
    "DIAG-1 full stack",
    feed=b"PING\nKDOWN|x\nHALT\n")
check("DIAG60a boot ok" in diag, "boot banner printed")
check("hid=yes" in diag and "dataport=yes" in diag and "sensor=yes" in diag and "arm=yes" in diag,
      "banner reports hid/dataport/sensor/arm all yes")
check("DIAG rx chunk n=3 hex=50494e" in diag, "first chunk logged with hex (PIN = 50 49 4e)")
check("DIAG rx line: PING" in diag, "assembled line PING logged")
check("DIAG tx: OK|PONG|pico-light 0.9.60" in diag, "PONG reply logged before writing")
check(any(l.startswith("OK|PONG|pico-light 0.9.60") and "role=brain" in l for l in ser.lines),
      "PONG still written to the data port (protocol intact)")
check("DIAG tx ERR|EXC|KDOWN" in diag and "ERR|EXC|KDOWN" in ser.lines,
      "malformed line logged AND answered ERR|EXC, loop survives")
check("DIAG rx line: HALT" in diag and "DIAG tx: OK|HALT" in diag and "OK|HALT" in ser.lines,
      "HALT logged and acked")
check("HALT" in g["arm"].written, "HALT still forwarded to the arm")
check("DIAG alive" in diag, "heartbeat printed in idle branch")
check(len(kbd["press"]) == 0, "no phantom keypress (AUTOSTART=False, no buttons)")

# ---- DIAG-2: keypad intact (the user's actual concern) ----
def btn_script2(n, b):
    if n == 50:
        b["GP4"].value = False   # Start/Stop
    if n == 60:
        b["GP4"].value = True
    if n == 70:
        b["GP3"].value = False   # Pause/Resume
    if n == 80:
        b["GP3"].value = True

g2, ser2, kbd2, btns2, diag2 = run_scenario("DIAG-2 keypad", feed=b"", btn_script=btn_script2)
check(kbd2["press"].count(2001) == 1, "GP4 tap sends exactly one KEYPAD_NUMLOCK to the PC")
check(kbd2["press"].count(2002) == 1, "GP3 tap sends exactly one SCROLL_LOCK to the PC")
check(g2["engine_on"] is True and g2["engine_paused"] is True,
      "GP4 started the engine, GP3 paused it (standalone contract intact)")

# ---- DIAG-3: sensor unplugged -> still boots, PING still answered ----
g3, ser3, kbd3, btns3, diag3 = run_scenario("DIAG-3 no sensor", sensor_ok=False, feed=b"PING\n")
check("sensor=no" in diag3, "banner reports sensor=no when unplugged")
check(any(l.startswith("OK|PONG|") for l in ser3.lines), "PING answered without the sensor")

# ---- hygiene: today's lessons encoded ----
code_only = "\n".join(l.split("#", 1)[0] for l in SRC.splitlines())
check("import os" not in code_only and "os.path" not in code_only, "no os import (v1 crash class)")
check("Keycode.NUM_LOCK" not in SRC, "never Keycode.NUM_LOCK (wrong name; probe bug class)")
check("Keycode.KEYPAD_NUMLOCK" in SRC, "keypad uses the real Keycode.KEYPAD_NUMLOCK")
check("errors=" not in SRC, "plain decode preserved (no errors kwarg)")
for marker in ("DIAG60a boot ok", "DIAG rx chunk", "DIAG rx line: ", "DIAG tx: ",
               "DIAG tx ERR|EXC|", "DIAG alive"):
    check(marker in SRC, "DIAG marker present: %r" % marker)

failed = [m for ok, m in results if not ok]
print()
print("=== sim60diag: %d passed, %d failed ===" % (len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
