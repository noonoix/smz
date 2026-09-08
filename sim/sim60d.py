# sim60d.py - sim of code60d.py under CircuitPython-10.3.0 semantics (no slice-delete),
# a slow-arm wedge scenario, AND the KTEXT typeText fix (kbd.write is absent on the
# board's adafruit_hid 6.1.10 - we now type via press/release + an ASCII map).
# Result at delivery: 20 passed / 0 failed. ASCII output only.
import contextlib
import io
import sys
import types

SRC = open("/data/code60d.py", encoding="utf-8").read()
compile(SRC, "code60d.py", "exec")
print("PASS: code60d compiles")

results = []
def check(cond, msg):
    results.append((bool(cond), msg))
    print(("PASS: " if cond else "FAIL: ") + msg)

class SimExit(BaseException):
    pass

class CPByteArray(bytearray):
    def __getitem__(self, key):
        r = super().__getitem__(key)
        if isinstance(key, slice):
            return CPByteArray(bytes(r))
        return r
    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise TypeError("'bytearray' object doesn't support item assignment")
        super().__setitem__(key, value)
    def __delitem__(self, key):
        if isinstance(key, slice):
            raise TypeError("'bytearray' object doesn't support item deletion")
        super().__delitem__(key)

def run_scenario(name, sensor_ok=True, arm_ok=True, feed=b"", calib=None,
                 sleep_limit=3000, btn_script=None, arm_evt=False):
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

    busio = types.ModuleType("busio")
    busio.I2C = FakeI2C
    busio.UART = FakeUART

    class FakeSerial:
        def __init__(self):
            self._in = bytearray(feed)
            self.lines = []
        @property
        def in_waiting(self):
            return min(3, len(self._in))
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
    usb_cdc.console = types.SimpleNamespace(connected=True)
    usb_hid = types.ModuleType("usb_hid")
    usb_hid.devices = []

    kbd_log = {"press": [], "release": [], "write": []}
    class FakeKeyboard:
        def __init__(self, devices):
            pass
        def press(self, *codes):
            for c in codes:
                kbd_log["press"].append(c)
        def release(self, *codes):
            for c in codes:
                kbd_log["release"].append(c)
        def write(self, ch):   # absent on the real 6.1.10 bundle; the firmware must NOT call it
            raise AttributeError("no write on this bundle")

    kc = types.SimpleNamespace()
    for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        setattr(kc, ch, 1000 + i)
    for i, nm in enumerate(("ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")):
        setattr(kc, nm, 1100 + i)
    for i in range(1, 25):
        setattr(kc, "F" + str(i), 1200 + i)
    for i, nm in enumerate(("PERIOD", "COMMA", "MINUS", "EQUALS", "FORWARD_SLASH", "SEMICOLON",
                            "QUOTE", "LEFT_BRACKET", "RIGHT_BRACKET", "BACKSLASH", "GRAVE_ACCENT")):
        setattr(kc, nm, 1300 + i)
    kc.ENTER = 13; kc.ESCAPE = 27; kc.SPACE = 32; kc.TAB = 9; kc.BACKSPACE = 8
    kc.LEFT_ARROW = 37; kc.RIGHT_ARROW = 39; kc.UP_ARROW = 38; kc.DOWN_ARROW = 40
    kc.LEFT_SHIFT = 160; kc.RIGHT_SHIFT = 161; kc.LEFT_CONTROL = 162; kc.RIGHT_CONTROL = 163
    kc.LEFT_ALT = 164; kc.RIGHT_ALT = 165; kc.LEFT_GUI = 91; kc.RIGHT_GUI = 92
    kc.SHIFT = 160
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
    g = {"__name__": "__main__", "open": fake_open, "bytearray": CPByteArray}
    cap = io.StringIO()
    try:
        try:
            with contextlib.redirect_stdout(cap):
                exec(compile(SRC, "code60d.py", "exec"), g)
        except SimExit:
            pass
    finally:
        for m in mods:
            if saved[m] is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = saved[m]
    diag = cap.getvalue()
    print("--- scenario %s: %d fake sleeps, %d PC lines" % (name, sleeps[0], len(serial_obj.lines)))
    return g, serial_obj, kbd_log, btns, diag


# ---- A: full stack (regression) ----
g, ser, kbd, btns, diag = run_scenario(
    "A full stack",
    feed=b"PING\nMMOVE|100,100,abs,0\nMMOVE|200,200,abs,0\nWSND|90,60,2000\nMCLICK|left,1\nKDOWN|x\nHALT\n")
check(any(l.startswith("OK|PONG|pico-light 0.9.60d") for l in ser.lines), "PING answered, version 0.9.60d")
check(not any(l == "OK|MMOVE" for l in ser.lines), "MMOVE fire-and-forget (no wedge)")
check("MMOVE|100,100,abs,0" in g["arm"].written, "MMOVE forwarded to the arm")
check("OK|MCLICK" in ser.lines, "MCLICK still acks")
check("OK|WSND" in ser.lines, "WSND round-trip")
check("OK|HALT" in ser.lines and "HALT" in g["arm"].written, "HALT acked + forwarded")

# ---- K1: typeText types via press/release (NOT kbd.write) ----
gK, serK, kbdK, btnsK, diagK = run_scenario("K1 typeText", feed=b"KTEXT|0,0,A1 b\n")
check("OK|KTEXT" in serK.lines, "KTEXT answers OK (no more ERR|EXC)")
check(kbdK["press"] == [160, 1000, 1101, 32, 1001],
      "typed A(shift)+1+space+b via press/release, got %s" % (kbdK["press"],))
check(kbdK["release"] == [1000, 160, 1101, 32, 1001], "shift released around the shifted key")

# ---- K2: an unmapped char -> graceful ERR|ASCII, nothing typed, loop survives ----
gK2, serK2, kbdK2, btnsK2, diagK2 = run_scenario("K2 bad char", feed="KTEXT|0,0,café\nPING\n".encode("utf-8"))
check("ERR|ASCII|KTEXT" in serK2.lines, "non-ASCII char -> ERR|ASCII|KTEXT (no crash)")
check(len(kbdK2["press"]) == 0, "bad char: nothing typed")
check(any(l.startswith("OK|PONG|") for l in serK2.lines), "loop survives after the KTEXT error")

# ---- FC: dense mouse flow control (regression from 60c) ----
burst = b"".join(b"MMOVE|%d,%d,abs,0\n" % (1000 + i, i) for i in range(20))
gF, serF, kbdF, btnsF, diagF = run_scenario("FC flow control", feed=burst)
moves = [w for w in gF["arm"].written if w.startswith("MMOVE")]
check("MMOVE|1019,19,abs,0" in moves and len(moves) == 9, "flow control intact: 8+1 flushed, final target lands")

# ---- B: keypad intact ----
def btn_script2(n, b):
    if n == 50: b["GP4"].value = False
    if n == 60: b["GP4"].value = True
    if n == 70: b["GP3"].value = False
    if n == 80: b["GP3"].value = True
g2, ser2, kbd2, btns2, diag2 = run_scenario("B keypad", feed=b"", btn_script=btn_script2)
check(kbd2["press"].count(2001) == 1 and kbd2["press"].count(2002) == 1, "keypad GP4/GP3 intact")

# ---- C: no sensor ----
g3, ser3, kbd3, btns3, diag3 = run_scenario("C no sensor", sensor_ok=False, feed=b"PING\n")
check(any(l.startswith("OK|PONG|") for l in ser3.lines), "PING answered without sensor")

# ---- hygiene ----
check("kbd.write(" not in SRC, "kbd.write call fully removed")
check("del buffer[" not in SRC and "del _arm_buf[" not in SRC, "no slice-delete anywhere")
check("def _ascii_key" in SRC and "_KTEXT_SHIFTED" in SRC, "ASCII map present")
check("pico-light 0.9.60d" in SRC, "version bumped to 0.9.60d")
check("import os" not in "\n".join(l.split('#',1)[0] for l in SRC.splitlines()), "no os import")

failed = [m for ok, m in results if not ok]
print()
print("=== sim60d: %d passed, %d failed ===" % (len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
