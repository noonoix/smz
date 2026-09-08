# sim-probe2.py - host-side simulation of code-probe2.py with stubbed CircuitPython modules.
# Proves the probe boots, logs chunks/lines, answers PING, keeps the keypad alive,
# and survives garbage bytes - without real hardware. ASCII output only.
# Runs in the Notion sandbox (/data paths). Result at delivery: 22 passed / 0 failed.
import contextlib
import io
import os
import sys
import threading
import time
import types

REAL = sys.stdout
def out(msg):
    REAL.write(msg + "\n")
    REAL.flush()

# ---------- stub CircuitPython modules (must exist before the probe is exec'd) ----------
class FakeCDC:
    def __init__(self):
        self.rx = bytearray()
        self.tx = bytearray()
    @property
    def in_waiting(self):
        return len(self.rx)
    def read(self, n=None):
        n = self.in_waiting if n is None else min(n, self.in_waiting)
        data = bytes(self.rx[:n]); del self.rx[:n]
        return data
    def write(self, b):
        self.tx.extend(b); return len(b)

data_cdc = FakeCDC()
usb_cdc = types.ModuleType("usb_cdc")
usb_cdc.data = data_cdc
usb_cdc.console = FakeCDC()
sys.modules["usb_cdc"] = usb_cdc

board = types.ModuleType("board")
board.GP3 = "GP3"; board.GP4 = "GP4"
sys.modules["board"] = board

digitalio = types.ModuleType("digitalio")
class Pull:
    UP = "UP"
digitalio.Pull = Pull
PIN = {"GP3": 1, "GP4": 1}   # pull-up idle level = 1; press = 0
class DigitalInOut:
    def __init__(self, gp):
        self.gp = gp
    def switch_to_input(self, pull=None):
        self.pull = pull
    @property
    def value(self):
        return PIN[self.gp] == 1
digitalio.DigitalInOut = DigitalInOut
sys.modules["digitalio"] = digitalio

usb_hid = types.ModuleType("usb_hid")
usb_hid.devices = ["fake-hid"]
sys.modules["usb_hid"] = usb_hid

ada = types.ModuleType("adafruit_hid")
sys.modules["adafruit_hid"] = ada
kb_mod = types.ModuleType("adafruit_hid.keyboard")
sys.modules["adafruit_hid.keyboard"] = kb_mod
kc_mod = types.ModuleType("adafruit_hid.keycode")
sys.modules["adafruit_hid.keycode"] = kc_mod
class Keycode:
    NUM_LOCK = 9001
    SCROLL_LOCK = 9002
kc_mod.Keycode = Keycode
PRESSES = []
class Keyboard:
    def __init__(self, devices):
        self.devices = devices
    def press(self, k):
        PRESSES.append(("down", k))
    def release(self, k):
        PRESSES.append(("up", k))
kb_mod.Keyboard = Keyboard

# ---------- run the probe in a daemon thread, stdout captured ----------
src = open("/data/code-probe2.py", encoding="utf-8").read()
logbuf = io.StringIO()
def run():
    with contextlib.redirect_stdout(logbuf):
        exec(compile(src, "code-probe2.py", "exec"), {"__name__": "__main__"})
threading.Thread(target=run, daemon=True).start()

def log():
    return logbuf.getvalue()

passed = 0
failed = 0
def check(ok, msg):
    global passed, failed
    if ok:
        passed += 1
        out("PASS: %s" % msg)
    else:
        failed += 1
        out("FAIL: %s" % msg)

def wait_for(cond, timeout=2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.02)
    return False

# ---------- scenario ----------
check(wait_for(lambda: "PROBE2 boot ok" in log()), "boot banner printed")
check("data_port=yes" in log(), "data port detected (not MISSING)")
check("hid=yes" in log(), "HID keypad initialized")
check(wait_for(lambda: "entering main loop" in log()), "main loop entered")

# PING -> PONG
data_cdc.rx.extend(b"PING\n")
ok = wait_for(lambda: b"PONG" in data_cdc.tx)
check(ok, "PING answered")
check(b"OK|PONG|pico-probe 2.0|role=brain+keyboard+light|arm=probe|hid=yes\n" in data_cdc.tx,
      "PONG payload exact (role=brain advertised for the app)")
check("PROBE2 rx chunk #1: %r" % (b"PING\n",) in log() or "rx chunk #1" in log(), "raw chunk logged")
check("PONG written: True" in log(), "PONG write logged")

# split line across two chunks
data_cdc.tx = bytearray()
data_cdc.rx.extend(b"PI")
time.sleep(0.25)
check(len(data_cdc.tx) == 0, "partial line gets no reply yet")
data_cdc.rx.extend(b"NG\n")
check(wait_for(lambda: b"PONG" in data_cdc.tx), "split PING answered after newline")

# garbage / invalid utf-8 then recovery
data_cdc.rx.extend(b"\xff\xfe\x00\n")
time.sleep(0.25)
data_cdc.tx = bytearray()
data_cdc.rx.extend(b"PING\n")
check(wait_for(lambda: b"PONG" in data_cdc.tx), "loop alive after invalid bytes")

# long line with no newline -> bounded buffer drop + discard-until-newline, loop survives
data_cdc.rx.extend(b"A" * 250)
check(wait_for(lambda: "overflow" in log()), "rx buffer overflow logged and dropped")
data_cdc.rx.extend(b"\n")   # newline terminates the garbage line (host retry style)
time.sleep(0.25)
data_cdc.tx = bytearray()
data_cdc.rx.extend(b"PING\n")
check(wait_for(lambda: b"PONG" in data_cdc.tx), "loop alive after overflow")

# HALT / BYE / unknown
data_cdc.tx = bytearray()
data_cdc.rx.extend(b"HALT\n")
check(wait_for(lambda: b"OK|HALT\n" in data_cdc.tx), "HALT acked")
data_cdc.tx = bytearray()
data_cdc.rx.extend(b"MMOVE|10,20\n")
check(wait_for(lambda: b"ERR|PROBE|MMOVE|10,20\n" in data_cdc.tx), "unknown command nacked (bridge never hangs)")

# keypad: GP4 press -> Num Lock HID; GP3 press -> Scroll Lock HID
PIN["GP4"] = 0
check(wait_for(lambda: ("down", 9001) in PRESSES and ("up", 9001) in PRESSES), "GP4 press -> Num Lock press+release")
PIN["GP4"] = 1
time.sleep(0.15)
PIN["GP3"] = 0
check(wait_for(lambda: ("down", 9002) in PRESSES and ("up", 9002) in PRESSES), "GP3 press -> Scroll Lock press+release")
PIN["GP3"] = 1
check("key press" in log(), "key presses logged on console")

# heartbeat
check(wait_for(lambda: "PROBE2 alive" in log(), timeout=3.0), "heartbeat printed every ~2 s")

# source hygiene: the v1 root bug must be impossible (check CODE only, not comments)
code_only = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
check("import os" not in code_only and "os.path" not in code_only, "probe never imports os (v1 crash class removed)")
check("errors=" not in src, "plain decode only (no errors kwarg)")
# ASCII-only console output: every print payload must be ascii-safe
import re
non_ascii_literals = [m for m in re.findall(r'"([^"\\]*)"', src) if any(ord(c) > 127 for c in m)]
check(len(non_ascii_literals) == 0, "all string literals ASCII (cp1252 console safe)")

out("SIM-PROBE2: %d passed / %d failed" % (passed, failed))
REAL.flush()
os._exit(1 if failed else 0)
