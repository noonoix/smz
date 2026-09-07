#!/usr/bin/env python3
"""sim60.py — shبیه‌سازی سخت‌افزار ساختگی برای قالب فرم‌ور v0.9.60 (قاعده‌ی ۳ طلایی).

ماژول‌های CircuitPython (board/busio/usb_cdc/usb_hid/digitalio/adafruit_hid) با
استاب‌های ضبط‌کننده جایگزین می‌شوند، قالب با placeholderهای پرشده exec می‌شود و
حلقه‌ی اصلی با یک BaseException (SimExit) بعد از N خواب ساختگی متوقف می‌شود —
همان‌طور که Ctrl+C واقعی هم از تور never-die عبور می‌کند (Exception نیست).
"""
import io
import json
import sys
import types

TEMPLATE = open("/data/firmware_template.py", encoding="utf-8").read()
FILLED = (TEMPLATE
          .replace("__MACHINE__", "SIM")
          .replace("__GENERATED__", "2026-09-08 01:30")
          .replace("__VERSION__", "0.9.60")
          .replace("__STATE_COUNT__", "1")
          .replace("__LOOP_MODE__", "forever")
          .replace("__LOOP_COUNT__", "0")
          .replace("__LOOP_SECONDS__", "0"))

# 0) syntax gate first (py_compile معادل — بدون import)
compile(FILLED, "code.py", "exec")
print("PASS: template compiles (filled)")

results = []


def check(cond, msg):
    results.append((bool(cond), msg))
    print(("PASS: " if cond else "FAIL: ") + msg)


class SimExit(BaseException):
    pass


def run_scenario(name, sensor_ok=True, lux=1200.0, arm_ok=True, feed=b"",
                 calib=None, sleep_limit=3000, btn_script=None, arm_evt=False):
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
                raise OSError("no sensor on the bus")
        def try_lock(self):
            return True
        def unlock(self):
            pass
        def writeto(self, addr, b):
            pass
        def readfrom_into(self, addr, buf):
            raw = int(lux * 1.2)
            buf[0] = (raw >> 8) & 0xFF
            buf[1] = raw & 0xFF

    class FakeUART:
        def __init__(self, *a, **k):
            if not arm_ok:
                raise OSError("no arm")
            self.written = []
            self._sched = []          # (ready_at, bytes)

        @property
        def in_waiting(self):
            return sum(len(b) for at, b in self._sched if at <= clock[0])

        def read(self, n=None):
            out = b""
            keep = []
            for at, b in self._sched:
                if at <= clock[0]:
                    out += b
                else:
                    keep.append((at, b))
            self._sched = keep
            return out

        def write(self, b):
            line = b.decode().strip()
            self.written.append(line)
            head = line.split("|")[0]
            if head == "WSND":
                if arm_evt:
                    self._sched.append((clock[0] + 0.02, b"EVT|TRG|react=90\n"))
                self._sched.append((clock[0] + 0.05, b"OK|WSND\n"))
            elif head in ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP"):
                self._sched.append((clock[0] + 0.10, ("OK|" + head + "\n").encode()))
            elif line in ("HALT", "BYE"):
                self._sched.append((clock[0] + 0.01, ("OK|" + line + "\n").encode()))
            return len(b)

        def inject(self, line, delay=0.0):
            self._sched.append((clock[0] + delay, line.encode() + b"\n"))

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
            out = bytes(self._in[:n])
            del self._in[:n]
            return out

        def write(self, b):
            self.lines.append(b.decode().strip())
            return len(b)

    serial_obj = FakeSerial()
    usb_cdc = types.ModuleType("usb_cdc")
    usb_cdc.data = serial_obj
    usb_cdc.console = None
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
            self.value = True               # pull-up: True = released
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
            return io.StringIO(json.dumps(calib))
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
    arm_obj = None
    try:
        try:
            exec(compile(FILLED, "code.py", "exec"), g)
        except SimExit:
            pass
    finally:
        for m in mods:
            if saved[m] is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = saved[m]
    print(f"--- scenario {name}: {sleeps[0]} fake sleeps, {len(serial_obj.lines)} PC lines")
    return g, serial_obj, kbd_log, btns


# ── A: full hardware, mixed command stream (split-feed included by the drip) ──
g, ser, kbd, btns = run_scenario(
    "A full stack",
    feed=(b"PING\n"
          b"WLUX|100,2000,100,5000,0\n"
          b"MCLICK|left,1\n"
          b"WSND|90,60,2000\n"
          b"KBDARM|KCOMBO|162+115,40,40\n"
          b"KDOWN|x\n"                       # malformed on purpose -> ERR|EXC, loop must survive
          b"LCAL|100\n"
          b"HALT\n"))
lines = ser.lines
check(any(l.startswith("OK|PONG|pico-light 0.9.60") and "role=brain" in l for l in lines),
      "A1: PING answered with the 0.9.60 brain identity")
check("OK|WLUX|lux=1200" in lines, "A2: WLUX stabilized at the fake 1200 lux")
check(lines.count("OK|MCLICK") == 1, "A3: MCLICK fire-and-ack answered exactly once (arm's own OK discarded by the pump)")
check(g["arm"].written.count("MCLICK|left,1") == 1, "A4: MCLICK was forwarded to the arm")
check("OK|WSND" in lines, "A5: blocking WSND returned the arm's real reply")
check(g["arm"].written.count("WSND|90,60,2000") == 1, "A6: WSND forwarded to the arm")
check("OK|KCOMBO" in lines and 162 in kbd["press"] and 1204 in kbd["press"],
      "A7: legacy KBDARM envelope consumed LOCALLY (Ctrl+F4 typed on the Pico)")
check(not any(w.startswith("KCOMBO") for w in g["arm"].written),
      "A8: no keyboard command ever reaches the arm (final contract)")
check("ERR|EXC|KDOWN" in lines, "A9: a malformed line yields ERR|EXC and the loop survives")
check(any(l.startswith("OK|LCAL|min=1200|max=1200|avg=1200") for l in lines),
      "A10: LCAL reports min/max/avg")
check("OK|HALT" in lines and "HALT" in g["arm"].written, "A11: HALT acked and forwarded to the arm")

# arm EVT streams live to the PC, even while a blocking command waits for its reply
g3, ser3, _, _ = run_scenario("A12 arm event", feed=b"PING\nWSND|90,60,2000\n", arm_evt=True)
lines3 = ser3.lines
check("EVT|TRG|react=90" in lines3 and "OK|WSND" in lines3
      and lines3.index("EVT|TRG|react=90") < lines3.index("OK|WSND"),
      "A12: an arm EVT streams to the PC live, before the blocking command's reply")

# ── B: sensor unplugged — the brain must stay alive ──
gB, serB, kbdB, _ = run_scenario("B no sensor", sensor_ok=False,
                                 feed=b"PING\nWLUX|1,2,3,4,0\nLCAL|100\nTRGLUX|1,2,3,4,0,69,0,0,40,40\n")
check(any(l.startswith("OK|PONG|") for l in serB.lines), "B1: PING answered without the sensor")
check("ERR|NOSENSOR|WLUX" in serB.lines, "B2: WLUX -> ERR|NOSENSOR")
check("ERR|NOSENSOR|LCAL" in serB.lines, "B3: LCAL -> ERR|NOSENSOR")
check("ERR|NOSENSOR|TRGLUX" in serB.lines, "B4: TRGLUX -> ERR|NOSENSOR")
check(len(kbdB["press"]) == 0, "B5: no phantom keypresses without a sensor")

# ── C: fixed keypad GP4/GP3 ──
def btn_script_c(n, b):
    if n == 50: b["GP4"].value = False      # press Start/Stop
    if n == 60: b["GP4"].value = True
    if n == 70: b["GP3"].value = False      # press Pause/Resume
    if n == 80: b["GP3"].value = True

gC, serC, kbdC, _ = run_scenario("C keypad", feed=b"", btn_script=btn_script_c)
check(kbdC["press"].count(2001) == 1, "C1: GP4 tap sends exactly one Num Lock to the PC")
check(kbdC["press"].count(2002) == 1, "C2: GP3 tap sends exactly one Scroll Lock to the PC")
check(gC["engine_on"] is True and gC["engine_paused"] is True,
      "C3: GP4 started the standalone engine, GP3 paused it")

# ── D: standalone engine fires armed states only when enabled ──
calib = {"states": [{"name": "s1", "luxLow": 100, "luxHigh": 2000, "stableMs": 100,
                     "timeoutMs": 20000, "mode": 0, "keyVk": 69, "key": "E", "armed": True}]}
gD, serD, kbdD, _ = run_scenario("D standalone idle", calib=calib, feed=b"", sleep_limit=200)
check(len(kbdD["press"]) == 0, "D1: AUTOSTART=False — boot never starts the macro by itself")

def btn_script_d2(n, b):
    # only GP4 (Start) — no pause press; the engine must fire after the 3s post-boot quiet window
    if n == 50: b["GP4"].value = False
    if n == 60: b["GP4"].value = True

gE, serE, kbdE, _ = run_scenario("D2 standalone armed", calib=calib, feed=b"",
                                 sleep_limit=400, btn_script=btn_script_d2)
check(kbdE["press"].count(1000 + ord("E") - ord("A")) >= 1,
      "D2: after GP4 the engine presses the armed state key (E)")
check(gE["passes"] >= 1, "D3: standalone pass counter advanced")

failed = [m for ok, m in results if not ok]
print()
print(f"=== sim60: {len(results) - len(failed)} passed, {len(failed)} failed ===")
sys.exit(1 if failed else 0)
