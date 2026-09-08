# sim60e.py - sim of code60e.py under CircuitPython-10.3.0 semantics (no slice-delete),
# with BEFORE/AFTER proofs against code60d.py for the three 60e fixes:
#   S1: a stale arm reply (late OK|HALT from an abort) must never be mis-paired as the
#       answer to the next SETRES (60d: returns OK|HALT = the hardware-log bug;
#       60e: pre-drain eats it, returns the arm's real OK|SETRES).
#   S2: HALT must wipe the 60c flow ledger (60d: a coalesced _pending_move survives an
#       abort and would flush into a later run = mystery jump; 60e: None).
#   S3: KTEXT pumps the arm mid-typing (60e: an arm EVT reaches the PC BEFORE OK|KTEXT;
#       60d: only after) while the per-key human pacing is preserved.
# Plus the 60d regression set. ASCII output only.
import contextlib
import io
import sys
import types

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

def run_scenario(name, src_path, sensor_ok=True, arm_ok=True, feed=b"", calib=None,
                 sleep_limit=3000, btn_script=None, arm_pre=None, arm_ack_mouse=True):
    SRC = open(src_path, encoding="utf-8").read()
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
            self._sched = [(clock[0] + dt, b) for dt, b in (arm_pre or [])]
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
                self._sched.append((clock[0] + 0.05, b"OK|WSND\n"))
            elif head in ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP"):
                if arm_ack_mouse:
                    self._sched.append((clock[0] + 0.10, ("OK|" + head + "\n").encode()))
            elif head == "SETRES":
                self._sched.append((clock[0] + 0.05, b"OK|SETRES\n"))
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
            self.line_times = []
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
            self.line_times.append(clock[0])
            return len(b)

    serial_obj = FakeSerial()
    usb_cdc = types.ModuleType("usb_cdc")
    usb_cdc.data = serial_obj
    usb_cdc.console = types.SimpleNamespace(connected=True)
    usb_hid = types.ModuleType("usb_hid")
    usb_hid.devices = []

    kbd_log = {"press": [], "release": []}
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
                exec(compile(SRC, src_path, "exec"), g)
        except SimExit:
            pass
    finally:
        for m in mods:
            if saved[m] is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = saved[m]
    print("--- scenario %s: %d fake sleeps, %d PC lines" % (name, sleeps[0], len(serial_obj.lines)))
    return g, serial_obj, kbd_log, btns

D = "/data/code60d.py"
E = "/data/code60e.py"

# ---- S1: stale arm reply must never answer a new SETRES ----
# the stale OK|HALT lands MID-COMMAND (+0.01s, while forward_to_arm waits) - exactly how a
# late abort answer arrives on the real wire; 60e's double-sweep window (20 ms) eats it.
gD, serD, kbdD, btnsD = run_scenario("S1-before (60d)", D,
    feed=b"SETRES|1920,1080\n", arm_pre=[(0.01, b"OK|HALT\n")])
check("OK|HALT" in serD.lines and "OK|SETRES" not in serD.lines,
      "S1 BEFORE: 60d mis-pairs the stale OK|HALT as the SETRES answer (the bug)")
gE, serE, kbdE, btnsE = run_scenario("S1-after (60e)", E,
    feed=b"SETRES|1920,1080\n", arm_pre=[(0.01, b"OK|HALT\n")])
check("OK|SETRES" in serE.lines and "OK|HALT" not in serE.lines,
      "S1 AFTER: 60e pre-drains the stale line; SETRES gets its real answer")

# ---- S2: HALT wipes the flow ledger (no stale coalesced move into the next run) ----
burst = b"".join(b"MMOVE|%d,%d,abs,0\n" % (1000 + i, i) for i in range(20))
gD2, serD2, kbdD2, btnsD2 = run_scenario("S2-before (60d)", D,
    feed=burst + b"HALT\n", arm_ack_mouse=False)   # arm never acks: lag stays, pending survives
check(gD2.get("_pending_move") == "MMOVE|1019,19,abs,0",
      "S2 BEFORE: 60d keeps the stale coalesced move after HALT (would flush later)")
gE2, serE2, kbdE2, btnsE2 = run_scenario("S2-after (60e)", E,
    feed=burst + b"HALT\n", arm_ack_mouse=False)
check(gE2.get("_pending_move") is None and gE2.get("_arm_lag") == 0,
      "S2 AFTER: 60e HALT wipes _pending_move + _arm_lag")
check("OK|HALT" in serE2.lines and "HALT" in gE2["arm"].written,
      "S2 AFTER: HALT still acked and forwarded to the arm")

# ---- S3: KTEXT pumps the arm mid-typing + pacing preserved ----
gD3, serD3, kbdD3, btnsD3 = run_scenario("S3-before (60d)", D,
    feed=b"KTEXT|90,180,abc\n", arm_pre=[(0.15, b"EVT|TRG|react=90\n")])
i_evtD = serD3.lines.index("EVT|TRG|react=90") if "EVT|TRG|react=90" in serD3.lines else 999
i_okD = serD3.lines.index("OK|KTEXT")
check(i_evtD > i_okD, "S3 BEFORE: 60d forwards the arm EVT only AFTER typing ends")
gE3, serE3, kbdE3, btnsE3 = run_scenario("S3-after (60e)", E,
    feed=b"KTEXT|90,180,abc\n", arm_pre=[(0.15, b"EVT|TRG|react=90\n")])
i_evtE = serE3.lines.index("EVT|TRG|react=90") if "EVT|TRG|react=90" in serE3.lines else 999
i_okE = serE3.lines.index("OK|KTEXT")
check(i_evtE < i_okE, "S3 AFTER: 60e pumps the arm mid-typing (EVT reaches the PC live)")
t_ok = serE3.line_times[i_okE] - 100.0
check(0.40 <= t_ok <= 0.85, "S3: per-key pacing preserved (OK|KTEXT at +%.2fs for 3 chars @90-180ms)" % t_ok)
check(kbdE3["press"] == [1000, 1001, 1002], "S3: typed a,b,c via press/release")

# ---- R1: regression - full stack on 60e ----
gR, serR, kbdR, btnsR = run_scenario("R1 full stack (60e)", E,
    feed=b"PING\nMMOVE|100,100,abs,0\nMMOVE|200,200,abs,0\nWSND|90,60,2000\nMCLICK|left,1\nHALT\n")
check(any(l.startswith("OK|PONG|pico-light 0.9.60e") for l in serR.lines), "R1: PING answers 0.9.60e")
check(not any(l == "OK|MMOVE" for l in serR.lines), "R1: MMOVE still fire-and-forget")
check("MMOVE|100,100,abs,0" in gR["arm"].written, "R1: MMOVE forwarded to the arm")
check("OK|MCLICK" in serR.lines, "R1: MCLICK still acks")
check("OK|WSND" in serR.lines, "R1: WSND round-trip")
check("OK|HALT" in serR.lines, "R1: HALT acked")

# ---- R2: KTEXT bad char -> graceful ERR, loop survives ----
gR2, serR2, kbdR2, btnsR2 = run_scenario("R2 bad char (60e)", E,
    feed="KTEXT|0,0,caf\u00e9\nPING\n".encode("utf-8"))
check("ERR|ASCII|KTEXT" in serR2.lines, "R2: non-ASCII -> ERR|ASCII|KTEXT (no crash)")
check(len(kbdR2["press"]) == 0, "R2: bad char types nothing")
check(any(l.startswith("OK|PONG|") for l in serR2.lines), "R2: loop survives the KTEXT error")

# ---- R3: dense-path flow control intact on 60e ----
gR3, serR3, kbdR3, btnsR3 = run_scenario("R3 flow control (60e)", E, feed=burst)
moves = [w for w in gR3["arm"].written if w.startswith("MMOVE")]
check("MMOVE|1019,19,abs,0" in moves and len(moves) == 9,
      "R3: flow control intact (8+1 flushed, final target lands)")

# ---- R4: boot without sensor still answers PING ----
gR4, serR4, kbdR4, btnsR4 = run_scenario("R4 no sensor (60e)", E, sensor_ok=False, feed=b"PING\n")
check(any(l.startswith("OK|PONG|") for l in serR4.lines), "R4: PING answered without sensor")

# ---- R5: KTEXT with hmax=0 types flat instantly (legacy fast mode untouched) ----
gR5, serR5, kbdR5, btnsR5 = run_scenario("R5 fast KTEXT (60e)", E, feed=b"KTEXT|0,0,ab\n")
i_ok5 = serR5.lines.index("OK|KTEXT")
check(serR5.line_times[i_ok5] - 100.0 < 0.35, "R5: KTEXT|0,0 stays instant (no forced pacing)")

# ---- hygiene ----
SRC_E = open(E, encoding="utf-8").read()
check("kbd.write(" not in SRC_E, "hygiene: no kbd.write call")
check("del buffer[" not in SRC_E and "del _arm_buf[" not in SRC_E, "hygiene: no slice-delete")
check("def _ascii_key" in SRC_E and "_KTEXT_SHIFTED" in SRC_E, "hygiene: ASCII map present")
check("def _flow_reset" in SRC_E, "hygiene: _flow_reset present")
check("pico-light 0.9.60e" in SRC_E, "hygiene: version 0.9.60e")

failed = [m for ok, m in results if not ok]
print()
print("=== sim60e: %d passed, %d failed ===" % (len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
