# lux-test v2 — BH1750 light-sensor test on Raspberry Pi Pico (CircuitPython)
# Wiring v6: SDA=GP20 · SCL=GP21 · ADDR->GND (0x23) · keypad common->GND · key1=GP2 · key2=GP3
# NEW in v2: key1 (GP2) = STOP the test · key2 (GP3) = PAUSE/RESUME
# Rename this file to code.py on CIRCUITPY to run it. To restore the real firmware,
# copy back the Classroom Studio v0.9.56 code.py afterwards.

import time
import board
import busio
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

ADDR = 0x23
POWER_ON = 0x01
RESET = 0x07
CONT_HIRES = 0x10   # 1 lux, ~120 ms per sample

TYPE_INTO_WINDOW = True   # False = only blink, no HID typing
PERIOD_S = 2.0            # seconds between samples
DARK_LUX = 30             # below this  -> DARK
BRIGHT_LUX = 800          # above this  -> BRIGHT (else mid)

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False


class Button:
    """Active-low button to GND with 40 ms software debounce; fires on press edge."""
    def __init__(self, pin):
        self._io = digitalio.DigitalInOut(pin)
        self._io.direction = digitalio.Direction.INPUT
        self._io.pull = digitalio.Pull.UP
        self._stable = True   # pull-up: True = released
        self._last = True
        self._t = time.monotonic()

    def pressed(self):
        now = time.monotonic()
        v = self._io.value
        if v != self._last:
            self._last = v
            self._t = now
        if v != self._stable and now - self._t >= 0.04:
            self._stable = v
            if not v:           # pulled to GND -> this is a press
                return True
        return False


btn1 = Button(board.GP2)   # key1 = STOP
btn2 = Button(board.GP3)   # key2 = PAUSE/RESUME


class Bh1750:
    def __init__(self, i2c, mode=CONT_HIRES):
        self._i2c = i2c
        self._buf = bytearray(2)
        self.mode = None
        self._cmd(POWER_ON)
        self._cmd(RESET)
        self.set_mode(mode)

    def _cmd(self, value):
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.writeto(ADDR, bytes([value]))
        finally:
            self._i2c.unlock()

    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self._cmd(mode)
        time.sleep(0.2 if mode == CONT_HIRES else 0.05)

    def lux(self):
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.readfrom_into(ADDR, self._buf)
        finally:
            self._i2c.unlock()
        raw = (self._buf[0] << 8) | self._buf[1]
        return raw / 1.2


kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)


def say(text):
    if TYPE_INTO_WINDOW:
        layout.write(text + "\n")


def blink(times, on_s, off_s):
    for _ in range(times):
        led.value = True
        time.sleep(on_s)
        led.value = False
        time.sleep(off_s)


i2c = busio.I2C(board.GP21, board.GP20)   # SCL, SDA
while not i2c.try_lock():
    pass
found = i2c.scan()
i2c.unlock()

if ADDR not in found:
    # Sensor not found: fast blink. key1 still exits cleanly.
    say("ERROR: BH1750 not found on I2C (0x23). check SDA=GP20 SCL=GP21")
    while True:
        blink(1, 0.08, 0.08)
        if btn1.pressed():
            say("stopped by key1")
            led.value = False
            raise SystemExit

sensor = Bh1750(i2c)
say("lux-test v2 started — key1(GP2)=stop key2(GP3)=pause")

n = 0
lo = None
hi = None
paused = False
next_sample = time.monotonic()
next_blink = time.monotonic()

while True:
    if btn1.pressed():
        say("STOPPED by key1 (GP2)")
        led.value = False
        break
    if btn2.pressed():
        paused = not paused
        say("paused" if paused else "resumed")

    now = time.monotonic()
    if paused:
        # double-blink while paused, no sampling
        if now >= next_blink:
            blink(2, 0.06, 0.06)
            next_blink = now + 1.0
        time.sleep(0.01)
        continue

    if now >= next_blink:      # healthy heartbeat: one short blink every ~4 s
        led.value = True
        time.sleep(0.03)
        led.value = False
        next_blink = now + 4.0

    if now >= next_sample:
        next_sample = now + PERIOD_S
        n += 1
        try:
            v = sensor.lux()
        except Exception:
            say("I2C read error — sensor loose?")
            continue
        lo = v if lo is None or v < lo else lo
        hi = v if hi is None or v > hi else hi
        cls = "DARK" if v < DARK_LUX else ("BRIGHT" if v > BRIGHT_LUX else "mid")
        say("n=%d lux=%d min=%d max=%d %s" % (n, v, lo, hi, cls))

    time.sleep(0.01)

say("test finished — copy back the real code.py firmware to use the app")
