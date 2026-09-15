# Classroom Studio — isolated read-only Pico light telemetry
# Firmware: pico-light-readonly 1.0.0
# Sensor: BH1750 / GY-30, I2C0, SDA=GP20, SCL=GP21, ADDR=GND => 0x23
# This file intentionally has no HID, keyboard, UART, macro, buzzer or actuator path.

import time
import board
import busio
import usb_cdc

VERSION = "1.0.0"
ADDR = 0x23
POWER_ON = 0x01
RESET = 0x07
CONT_HIRES = 0x10

serial = usb_cdc.data
_buffer = bytearray()
_sequence = 0


class Bh1750:
    def __init__(self, i2c):
        self.i2c = i2c
        self.buf = bytearray(2)
        self._write(POWER_ON)
        self._write(RESET)
        self._write(CONT_HIRES)
        time.sleep(0.20)

    def _write(self, value):
        deadline = time.monotonic() + 1.0
        while not self.i2c.try_lock():
            if time.monotonic() >= deadline:
                raise RuntimeError("I2C lock timeout")
            time.sleep(0.001)
        try:
            self.i2c.writeto(ADDR, bytes((value,)))
        finally:
            self.i2c.unlock()

    def read_lux(self):
        deadline = time.monotonic() + 1.0
        while not self.i2c.try_lock():
            if time.monotonic() >= deadline:
                raise RuntimeError("I2C lock timeout")
            time.sleep(0.001)
        try:
            self.i2c.readfrom_into(ADDR, self.buf)
        finally:
            self.i2c.unlock()
        raw = (self.buf[0] << 8) | self.buf[1]
        return raw / 1.2


try:
    # BH1750 / GY-30: Pico GP21=SCL, GP20=SDA, ADDR tied to GND.
    _i2c = busio.I2C(board.GP21, board.GP20)
    sensor = Bh1750(_i2c)
except Exception:
    sensor = None


def send(line):
    if serial is not None:
        try:
            serial.write((line + "\n").encode("utf-8"))
        except Exception:
            pass


def lux_reply():
    global _sequence
    if sensor is None:
        return "ERR|NOSENSOR|LUX"
    try:
        value = sensor.read_lux()
        if value != value or value < 0:
            return "ERR|I2C|LUX"
        _sequence = (_sequence + 1) & 0xFFFFFFFF
        return "OK|LUX|seq=%d|lux=%.1f|mode=hires|sensor=ok" % (_sequence, value)
    except Exception:
        return "ERR|I2C|LUX"


def handle(line):
    if line == "PING":
        return "OK|PONG|pico-light-readonly %s|role=light-readonly|hid=off|actuator=off" % VERSION
    if line == "LUX?":
        return lux_reply()
    if line == "HALT":
        return "OK|HALT"
    if line == "BYE":
        return "OK|BYE"
    # Every other command is rejected and has no side effect.
    head = line.split("|", 1)[0][:32]
    return "ERR|READONLY|" + head


while True:
    try:
        if serial is None:
            time.sleep(1.0)
            continue
        waiting = serial.in_waiting
        if waiting:
            _buffer.extend(serial.read(waiting))
            if len(_buffer) > 1024:
                del _buffer[:-512]
            while True:
                newline = _buffer.find(b"\n")
                if newline < 0:
                    break
                raw = bytes(_buffer[:newline])
                del _buffer[:newline + 1]
                line = raw.decode("utf-8", "replace").strip()
                if line:
                    send(handle(line))
        else:
            time.sleep(0.01)
    except Exception:
        # Keep the read-only endpoint alive after malformed input or USB noise.
        time.sleep(0.05)
