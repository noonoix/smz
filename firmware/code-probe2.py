# code-probe2.py - Pico data-port diagnostic probe (CircuitPython-safe)
# Classroom Studio - diagnosis build. NOT the real firmware: no arm bridge, no macro engine.
# What it does:
#   1. logs to the console port (COM3) every raw chunk that arrives on the DATA port
#   2. logs every assembled line and every reply written back
#   3. answers PING with PONG so the app's brain probe can connect
#   4. keeps the keypad alive: GP4->GND = Num Lock (start/stop), GP3->GND = Scroll Lock (pause/resume)
#
# v2 fix: probe v1 crashed at boot (line 22) because it touched os.path - CircuitPython
# has no os.path. This probe never imports os. All console output is ASCII-only so a
# cp1252 Windows console can never kill the logger.

import time

import board
import digitalio
import usb_cdc

FW = "pico-probe 2.0"
data = usb_cdc.data

# --- optional HID keypad (never fatal) ---
kbd = None
NUM_LOCK = None
SCROLL_LOCK = None
try:
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    kbd = Keyboard(usb_hid.devices)
    NUM_LOCK = Keycode.NUM_LOCK
    SCROLL_LOCK = Keycode.SCROLL_LOCK
    hid_ok = True
except Exception:
    hid_ok = False

def clog(msg):
    try:
        print(msg)
    except Exception:
        pass

clog("PROBE2 boot ok | fw=%s | hid=%s | data_port=%s" % (FW, "yes" if hid_ok else "no", "yes" if data is not None else "MISSING"))

# --- keypad: GP4 = Num Lock, GP3 = Scroll Lock (pull-up, press = LOW, 40 ms debounce) ---
keys = []
try:
    for gp, code in ((board.GP4, NUM_LOCK), (board.GP3, SCROLL_LOCK)):
        pin = digitalio.DigitalInOut(gp)
        pin.switch_to_input(pull=digitalio.Pull.UP)
        keys.append([pin, code, 1, 0.0])   # pin, keycode, last_level, last_edge_monotonic
except Exception as e:
    clog("PROBE2 keypad init failed: %r" % (e,))
    keys = []

def pump_keys():
    if not hid_ok:
        return
    now = time.monotonic()
    for st in keys:
        lvl = 1 if st[0].value else 0
        if lvl != st[2] and now - st[3] >= 0.04:
            st[2] = lvl
            st[3] = now
            if lvl == 0 and st[1] is not None:
                try:
                    kbd.press(st[1])
                    kbd.release(st[1])
                    clog("PROBE2 key press: %s" % ("NumLock" if st[1] == NUM_LOCK else "ScrollLock"))
                except Exception as e:
                    clog("PROBE2 hid write failed: %r" % (e,))

def write_data(text):
    if data is None:
        clog("PROBE2 cannot reply: data port MISSING")
        return False
    try:
        data.write(text.encode("utf-8"))
        return True
    except Exception as e:
        clog("PROBE2 reply write failed: %r" % (e,))
        return False

def handle_line(line):
    cmd = line.strip()
    clog("PROBE2 rx line: %r" % cmd)
    if cmd == "PING":
        ok = write_data("OK|PONG|%s|role=brain+keyboard+light|arm=probe|hid=%s\n" % (FW, "yes" if hid_ok else "no"))
        clog("PROBE2 PONG written: %s" % ok)
    elif cmd == "HALT":
        clog("PROBE2 ack HALT: %s" % write_data("OK|HALT\n"))
    elif cmd == "BYE":
        clog("PROBE2 ack BYE: %s" % write_data("OK|BYE\n"))
    elif cmd:
        clog("PROBE2 nack unknown: %s" % write_data("ERR|PROBE|%s\n" % cmd[:24]))

buf = bytearray()
discard = False   # after an overflow, drop everything until the next '\n' (line boundary resync)
chunks_seen = 0
last_beat = time.monotonic()
clog("PROBE2 entering main loop - watching the data port...")

while True:
    try:
        if data is not None and data.in_waiting:
            chunk = data.read(data.in_waiting)
            if chunk:
                chunks_seen += 1
                clog("PROBE2 rx chunk #%d: %r" % (chunks_seen, bytes(chunk)))
                for b in chunk:
                    if b == 10:                        # '\n'
                        discard = False
                        try:
                            line = bytes(buf).decode("utf-8")   # plain decode: no errors kwarg
                        except Exception:
                            line = ""
                        buf = bytearray()
                        handle_line(line)
                    elif discard:
                        pass                           # inside an over-long garbage line
                    elif b != 13:                      # drop '\r'
                        buf.append(b)
                        if len(buf) > 192:
                            clog("PROBE2 rx buffer overflow - dropping until next newline (%d bytes)" % len(buf))
                            buf = bytearray()
                            discard = True
        pump_keys()
        now = time.monotonic()
        if now - last_beat >= 2.0:
            last_beat = now
            clog("PROBE2 alive | chunks=%d" % chunks_seen)
        time.sleep(0.02)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        clog("PROBE2 loop guard caught: %r" % (e,))
        time.sleep(0.2)
