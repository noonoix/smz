#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch-v0.9.59.py — «پیکو = مغز زنده‌ی اجرا» برای Classroom Studio

ریشه‌ی مشکل: bridge.py همیشه با BoardLink (هندشیک رمزشده‌ی HELLO/AES مخصوص
فرم‌ور ۱٫۶ پرو میکرو) وصل می‌شد؛ فرم‌ور pico-light پیکو متن‌باز حرف می‌زند و
هندشیک را پاس نمی‌دهد ← پیکو در اجرا هیچ نقشی نداشت، همه‌ی فرمان‌ها مستقیم به
پرو میکرو می‌رفت و کالیبراسیون زنده‌ی نور ممکن نبود.

این پچ:
  ۱) bridge.py ← کلاس PicoLink (لینک متن‌باز با همان رابط BoardLink) + تابع
     open_link (مغز اول، fallback به مسیر رمزشده) + فیلد role در رویداد connected
  ۲) tools/test_bridge_pico.py ← تست رفتاری ۱۶موردی با پیکوی جعلی (بدون سخت‌افزار)
  ۳) .github/workflows/build.yml ← قدم اجرای این تست در CI

اجرای دوم بی‌اثر است (idempotent). قبل از نوشتن، کنار هر فایل .bak-v0.9.59 ساخته
می‌شود. پایان کار: py_compile + اجرای واقعی تست رفتاری به‌عنوان خودتأییزی.

اجرا از ریشه‌ی ریپو:   python .\\patch-v0.9.59.py .
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
BRIDGE = os.path.join(ROOT, "ams-shell", "bridge", "bridge.py")
TESTF = os.path.join(ROOT, "tools", "test_bridge_pico.py")
WF = os.path.join(ROOT, ".github", "workflows", "build.yml")


def fail(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def backup(path):
    bak = path + ".bak-v0.9.59"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)


# ── ۱) bridge.py ────────────────────────────────────────────────────
if not os.path.exists(BRIDGE):
    fail("bridge.py پیدا نشد: " + BRIDGE + " — از ریشه‌ی ریپو اجرا کن")
s = open(BRIDGE, encoding="utf-8").read()

if "class PicoLink" in s and "def open_link" in s:
    print("already patched: ams-shell/bridge/bridge.py")
else:
    old_doc = 'اجرا:\n  python bridge.py --pydir'
    new_doc = ('v0.9.59 — انتخاب خودکار لینک در connect: اگر پورت به PING با role=brain/pico-light\n'
               '  جواب داد (پیکو)، لینک متن‌باز PicoLink بدون نیاز به ams_key.json — کیبورد و نور\n'
               '  همان‌جا روی پیکو و فرمان‌های بازو روی UART به پرو میکرو پاس داده می‌شوند؛\n'
               '  وگرنه همان BoardLink رمزشده‌ی همیشگی برای اتصال مستقیم به پرو میکرو.\n'
               'اجرا:\n  python bridge.py --pydir')
    if s.count(old_doc) != 1:
        fail("لنگر docstring در bridge.py یکتا نیست")
    s = s.replace(old_doc, new_doc)

    anchor = "\n\ndef main():"
    if s.count(anchor) != 1:
        fail("لنگر def main در bridge.py یکتا نیست")
    block = '''

class PicoError(Exception):
    pass


class PicoLink:
    """v0.9.59 — لینک متن‌باز با مغز پیکو (فرم‌ور pico-light روی پورت data).

    پیکو همان‌جا کیبورد HID و سنسور نور را اجرا می‌کند و فرمان‌های بازو
    (MMOVE/WSND/…) را روی UART به پرو میکرو پاس می‌دهد؛ پس اپ دیگر مستقیم
    با برد حرف نمی‌زند. همان رابط BoardLink (connect/command/_send/close/events)
    را پیاده می‌کند تا حلقهٔ worker فرقی بین دو لینک نبیند. بدون رمزنگاری و
    بدون نیاز به ams_key.json — کانال PC↔Pico متن‌باز است؛ مسیر رمزشده فقط
    برای اتصال مستقیم به پرو میکرو (BoardLink) باقی می‌ماند.
    """

    def __init__(self, port="AUTO", baud=115200, settle_s=1.0):
        self.port = port
        self.baud = baud
        self.settle_s = settle_s
        self.ser = None
        self.fw_ver = None
        self.role = "brain"        # در رویداد connected به اپ می‌رسد
        self.events = []           # خطوط EVT که وسط پاسخ‌ها رسیدند
        self.tx = 0
        self.rx = 0
        self._rxbuf = bytearray()

    def connect(self):
        import serial
        self.ser = serial.Serial(self.port, self.baud, timeout=0.2, write_timeout=2)
        time.sleep(self.settle_s)   # پورت data پیکو با باز شدن، برد را ریست نمی‌کند
        self._rxbuf.clear()
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass
        pong = self.command("PING", timeout=2.5)
        if "role=brain" not in pong and "pico-light" not in pong:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            raise PicoError("این پورت مغز پیکو نیست: " + pong[:60])
        # "OK|PONG|pico-light x|role=brain…|arm=promicro" ← هویت برای LEDهای اپ
        self.fw_ver = pong[len("OK|PONG|"):] if pong.startswith("OK|PONG|") else pong
        return self.port

    def command(self, cmd, timeout=5.0):
        if self.ser is None:
            raise PicoError("not connected")
        self._send(cmd)
        deadline = time.monotonic() + timeout
        while True:
            line = self._read_line(max(0.05, deadline - time.monotonic()))
            if line is None:
                raise PicoError("ERR|TIMEOUT|" + cmd.split("|")[0])
            if line.startswith("EVT|"):
                self.events.append(line)   # رویداد مسلح، جایگزین پاسخ نمی‌شود
                continue
            return line

    def _send(self, text):
        if self.ser is None:
            raise PicoError("not connected")
        self.ser.write(text.encode("ascii") + b"\\n")
        self.ser.flush()
        self.tx += 1

    def _read_line(self, timeout=0.5):
        """یک خط کامل؛ بایت‌های نیمه‌تمام در بافر می‌مانند (همان قاعدهٔ ams_serial)."""
        end = time.monotonic() + timeout
        while True:
            nl = self._rxbuf.find(b"\\n")
            if nl >= 0:
                raw = bytes(self._rxbuf[:nl])
                del self._rxbuf[:nl + 1]
                self.rx += 1
                return raw.decode("utf-8", "replace").strip()
            if time.monotonic() >= end:
                return None
            chunk = self.ser.read(64)
            if chunk:
                self._rxbuf += chunk
            else:
                time.sleep(0.02)

    def halt(self):
        try:
            self._send("HALT")
        except Exception:
            pass

    def close(self):
        try:
            if self.ser is not None:
                self._send("HALT")
                self._send("BYE")
        except Exception:
            pass
        try:
            if self.ser is not None:
                self.ser.close()
        except Exception:
            pass
        self.ser = None


def open_link(port):
    """v0.9.59 — مغز پیکو اول، بازوی رمزشده به‌عنوان fallback.

    روی پورت PING می‌فرستد: پاسخ با role=brain/pico-light ← PicoLink متن‌باز؛
    هر پاسخ/سکوت دیگر ← همان BoardLink رمزشده‌ی همیشگی (پرو میکرو مستقیم).
    """
    link = PicoLink(port=port)
    try:
        dev = link.connect()
        return link, dev
    except Exception:
        try:
            link.close()
        except Exception:
            pass
    from ams_serial import BoardLink   # import تنبل — مسیر پیکو به ams_key.json نیاز ندارد
    link = BoardLink(port=port)
    dev = link.connect()
    return link, dev


def main():'''
    s = s.replace(anchor, block, 1)

    old_op = '''                    emit({"event": "stage", "stage": "port_open", "port": port})
                    link = BoardLink(port=port)
                    dev = link.connect()
                    state["link"] = link
                    emit({"event": "stage", "stage": "hello_ok", "fw": dev})
                    emit({"event": "connected", "port": dev, "fw": link.fw_ver})'''
    new_op = '''                    emit({"event": "stage", "stage": "port_open", "port": port})
                    # v0.9.59 — مغز پیکو اول: لینک متن‌باز pico-light اگر PING با
                    # role=brain جواب داد؛ وگرنه همان BoardLink رمزشده برای پرو میکرو.
                    link, dev = open_link(port)
                    state["link"] = link
                    emit({"event": "stage", "stage": "hello_ok", "fw": dev})
                    emit({"event": "connected", "port": dev, "fw": link.fw_ver, "role": getattr(link, "role", None)})'''
    if s.count(old_op) != 1:
        fail("لنگر connect op در bridge.py یکتا نیست")
    s = s.replace(old_op, new_op)

    backup(BRIDGE)
    open(BRIDGE, "w", encoding="utf-8", newline="").write(s)
    print("OK: patched ams-shell/bridge/bridge.py")

# ── ۲) تست رفتاری ───────────────────────────────────────────────────
TEST_CONTENT = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/test_bridge_pico.py — v0.9.59 behavior test for the Pico brain transport.

Runs WITHOUT hardware and WITHOUT pyserial: a fake `serial` module (and a stub
`ams_serial`) is injected into sys.modules before importing bridge.py, so
PicoLink talks to a scripted fake Pico data port. CI runs this on every push.

Scenarios:
 1. brain-first connect: PING→role=brain picks PicoLink, BoardLink never built
 2. keyboard command executes on the Pico (KTEXT → OK|KTEXT)
 3. arm command flows through the brain (MMOVE → forwarded reply OK|MMOVE)
 4. an EVT line mid-command is queued to link.events, NOT mispaired as reply
 5. a reply split into tiny reads still parses (partial-line buffering)
 6. silence raises a timeout naming the command head (ERR|TIMEOUT|…)
 7. a non-brain port falls back to the encrypted BoardLink path
 8. HALT goes out as a bare write (abort path), close() sends HALT+BYE
"""
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE_DIR = os.path.normpath(os.path.join(HERE, "..", "ams-shell", "bridge"))
sys.path.insert(0, BRIDGE_DIR)

PASSED = 0


def check(label, cond):
    global PASSED
    if not cond:
        print("FAIL: " + label)
        sys.exit(1)
    PASSED += 1
    print("PASS: " + label)


class FakePort:
    """Scripted stand-in for the Pico's USB data port (or any serial device)."""

    def __init__(self, script, name="COM5"):
        self.name = name
        self.script = script          # list of (match_substr, [reply lines])
        self.written = []
        self._rx = bytearray()
        self.closed = False
        self.chunk = 10 ** 9          # lowered in scenario 5 to force split reads

    # --- pyserial surface used by PicoLink ---
    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def write(self, data):
        data = bytes(data)
        self.written.append(data)
        line = data.decode("utf-8", "replace").strip()
        for want, replies in self.script:
            if want in line:
                for r in replies:
                    self._rx += r.encode("utf-8") + b"\n"
        return len(data)

    def flush(self):
        pass

    def read(self, n=64):
        if not self._rx:
            time.sleep(0.005)
            return b""
        n = min(n, self.chunk, len(self._rx))
        out = bytes(self._rx[:n])
        del self._rx[:n]
        return out

    def close(self):
        self.closed = True


def fake_serial_module(port):
    mod = types.ModuleType("serial")
    mod.Serial = lambda device, baud, **kw: port
    return mod


# stub ams_serial: records every BoardLink construction/connection attempt
BOARDLINK_CALLS = {"built": 0, "connected": 0}


def fake_ams_serial_module():
    mod = types.ModuleType("ams_serial")

    class BoardError(Exception):
        pass

    class BoardLink:
        def __init__(self, port="AUTO", **kw):
            BOARDLINK_CALLS["built"] += 1
            self.port = port
            self.fw_ver = "1.6"
            self.events = []

        def connect(self):
            BOARDLINK_CALLS["connected"] += 1
            return self.port

        def close(self):
            pass

    mod.BoardError = BoardError
    mod.BoardLink = BoardLink
    return mod


def fresh_bridge(port, boardlink_stub=True):
    """Import bridge.py with fake serial + stub ams_serial around `port`."""
    sys.modules.pop("bridge", None)
    sys.modules["serial"] = fake_serial_module(port)
    sys.modules["serial.tools"] = types.ModuleType("serial.tools")
    if boardlink_stub:
        sys.modules["ams_serial"] = fake_ams_serial_module()
        sys.modules["ams_crypto"] = types.ModuleType("ams_crypto")
    import bridge
    return bridge


BRAIN_PONG = "OK|PONG|pico-light 0.9.58|role=brain+keyboard+light|arm=promicro"

# ── scenario 1-4: full brain session ─────────────────────────────────
pico = FakePort([
    ("PING", [BRAIN_PONG]),
    ("KTEXT", ["OK|KTEXT"]),
    ("MMOVE", ["OK|MMOVE"]),
    ("WSND", ["EVT|TRG|react=123", "OK|WSND|fired"]),   # EVT BEFORE the reply
])
br = fresh_bridge(pico)
link, dev = br.open_link("COM5")

check("1a: brain-first connect returns a PicoLink", type(link).__name__ == "PicoLink")
check("1b: connected device is the probed port", dev == "COM5")
check("1c: identity carries role=brain for the app LEDs",
      "role=brain" in (link.fw_ver or "") and "pico-light" in (link.fw_ver or ""))
check("1d: encrypted BoardLink was never constructed for a brain port",
      BOARDLINK_CALLS["built"] == 0)
check("1e: role metadata for the connected event", getattr(link, "role", None) == "brain")

reply = link.command("KTEXT|0,0,E", timeout=1.0)
check("2: keyboard step executes on the Pico itself", reply == "OK|KTEXT")

reply = link.command("MMOVE|100,200,abs,1", timeout=1.0)
check("3: arm command flows PC→Pico→arm and its reply returns", reply == "OK|MMOVE")

reply = link.command("WSND|500,100,2000", timeout=2.0)
check("4a: real reply wins over an interleaved EVT", reply == "OK|WSND|fired")
check("4b: the armed EVT was queued to events, not lost, not mispaired",
      link.events == ["EVT|TRG|react=123"])

# ── scenario 5: split reads ──────────────────────────────────────────
pico2 = FakePort([("PING", [BRAIN_PONG]), ("LCAL", ["OK|LCAL|min=55|max=59|avg=57"])])
pico2.chunk = 3            # every read() returns at most 3 bytes
br2 = fresh_bridge(pico2)
link2, _ = br2.open_link("COM5")
reply = link2.command("LCAL|3000", timeout=2.0)
check("5: reply split into 3-byte reads still parses", reply == "OK|LCAL|min=55|max=59|avg=57")

# ── scenario 6: silence → clean timeout ──────────────────────────────
pico3 = FakePort([("PING", [BRAIN_PONG])])               # answers PING only
br3 = fresh_bridge(pico3)
link3, _ = br3.open_link("COM5")
try:
    link3.command("WLUX|100,200,1000,500,0", timeout=0.3)
    check("6: silent command must time out", False)
except Exception as e:
    check("6: silence raises a timeout naming the command head",
          "ERR|TIMEOUT|WLUX" in str(e))

# ── scenario 7: plain arm board → encrypted fallback ─────────────────
arm = FakePort([("PING", ["OK|PONG|ams-board 1.6"])])    # no role=brain
br4 = fresh_bridge(arm)
link4, dev4 = br4.open_link("COM17")
check("7a: non-brain port falls back to BoardLink", type(link4).__name__ == "BoardLink")
check("7b: fallback connected to the same port", dev4 == "COM17")
check("7c: fallback really used the encrypted path",
      BOARDLINK_CALLS["built"] >= 1 and BOARDLINK_CALLS["connected"] >= 1)

# ── scenario 8: abort/close writes ───────────────────────────────────
link._send("HALT")
check("8a: abort path writes a bare HALT line", pico.written[-1] == b"HALT\n")
link.close()
check("8b: close sends HALT then BYE and closes the port",
      pico.written[-2] == b"HALT\n" and pico.written[-1] == b"BYE\n" and pico.closed)

print("=== bridge pico transport: %d checks passed, 0 failed ===" % PASSED)
'''

if os.path.exists(TESTF) and "PicoLink" in open(TESTF, encoding="utf-8").read():
    print("already present: tools/test_bridge_pico.py")
else:
    os.makedirs(os.path.dirname(TESTF), exist_ok=True)
    open(TESTF, "w", encoding="utf-8", newline="").write(TEST_CONTENT)
    print("OK: wrote tools/test_bridge_pico.py")

# ── ۳) قدم CI ───────────────────────────────────────────────────────
if not os.path.exists(WF):
    fail("workflow پیدا نشد: " + WF)
w = open(WF, encoding="utf-8").read()
if "test_bridge_pico" in w:
    print("already patched: .github/workflows/build.yml")
else:
    wanchor = "      - name: Restore\n        run: dotnet restore ams-shell/AMS.sln"
    if w.count(wanchor) != 1:
        fail("لنگر Restore در build.yml یکتا نیست")
    step = ("      # v0.9.59 — the Pico brain transport is behavior-tested with a fake data port\n"
            "      - name: Behavior-test Pico brain transport\n"
            "        run: python tools/test_bridge_pico.py\n\n")
    w = w.replace(wanchor, step + wanchor, 1)
    backup(WF)
    open(WF, "w", encoding="utf-8", newline="").write(w)
    print("OK: patched .github/workflows/build.yml")

# ── خودتأییزی: کامپایل + تست رفتاری واقعی ───────────────────────────
print("\n--- self-check: py_compile bridge.py ---")
subprocess.run([sys.executable, "-m", "py_compile", BRIDGE], check=True)
print("--- self-check: behavior test ---")
res = subprocess.run([sys.executable, TESTF])
if res.returncode != 0:
    fail("تست رفتاری قرمز شد — push نکن؛ خروجی را بفرست")

print("\nتمام شد ✅ — سه فایل آماده‌اند:")
print("  ams-shell/bridge/bridge.py   (PicoLink + open_link)")
print("  tools/test_bridge_pico.py    (۱۶ چک رفتاری، تازه)")
print("  .github/workflows/build.yml  (قدم CI تازه)")
print("\nپیشنهاد commit/push:")
print('  git add ams-shell/bridge/bridge.py tools/test_bridge_pico.py .github/workflows/build.yml')
print('  git commit -m "feat(bridge): v0.9.59 — Pico live-brain transport (PicoLink, brain-first) + behavior test"')
print("  git push")
