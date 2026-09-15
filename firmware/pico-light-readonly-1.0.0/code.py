# Classroom Studio — isolated read-only Pico light telemetry
# Firmware: pico-light-readonly 1.0.2
# Sensor: BH1750 / GY-30, I2C0, SDA=GP20, SCL=GP21, ADDR=GND => 0x23
# This file intentionally has no HID, keyboard, UART, macro, buzzer or actuator path.

import time
import board
import busio
import usb_cdc

VERSION = "1.0.2"
ADDR = 0x23
POWER_ON = 0x01
RESET = 0x07
CONT_HIRES = 0x10

_channels = []
for _candidate in (usb_cdc.data, usb_cdc.console):
    if _candidate is not None and all(_candidate is not _item for _item in _channels):
        _channels.append(_candidate)
_buffers = [bytearray() for _ in _channels]
for _channel in _channels:
    try:
        _channel.timeout = 0.0
    except Exception:
        pass
_sequence = 0
_i2c = None
_sensor = None
_sensor_attempted = False


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


def ensure_sensor():
    global _i2c, _sensor, _sensor_attempted
    if _sensor_attempted:
        return _sensor
    _sensor_attempted = True
    try:
        # Do not touch I2C during boot: PING must remain available even when
        # the sensor is absent or its wiring is not yet ready.
        _i2c = busio.I2C(board.GP21, board.GP20)
        _sensor = Bh1750(_i2c)
    except Exception:
        _sensor = None
    return _sensor


def send(channel, line):
    if channel is not None:
        try:
            channel.write((line + "\n").encode("utf-8"))
        except Exception:
            pass


def lux_reply():
    global _sequence
    sensor = ensure_sensor()
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


def poll_channel(channel, buffer):
    try:
        chunk = channel.read(64)
    except Exception:
        return
    if not chunk:
        return
    buffer.extend(chunk)
    if len(buffer) > 1024:
        del buffer[:-512]
    while True:
        newline = buffer.find(b"\n")
        if newline < 0:
            return
        raw = bytes(buffer[:newline])
        del buffer[:newline + 1]
        line = raw.decode("utf-8", "replace").strip()
        if line:
            send(channel, handle(line))


while True:
    try:
        for _index, _channel in enumerate(_channels):
            poll_channel(_channel, _buffers[_index])
        time.sleep(0.01)
    except Exception:
        # Keep the read-only endpoint alive after malformed input or USB noise.
        time.sleep(0.05)
