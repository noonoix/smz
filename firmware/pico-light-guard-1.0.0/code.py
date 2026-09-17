# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# Parse the Guard bundle on a fresh heap, provide CircuitPython compatibility
# shims, and defer the 57 KB plan engine until route execution.
import gc
import sys
import os as _real_os
import hashlib as _real_hashlib

class _PathCompat:
    @staticmethod
    def join(root, name):
        if not root or root == "/":
            return "/" + name.lstrip("/")
        return root.rstrip("/") + "/" + name.lstrip("/")

    @staticmethod
    def isfile(path):
        try:
            return (_real_os.stat(path)[0] & 0x4000) == 0
        except OSError:
            return False

class _OsCompat:
    path = _PathCompat()

    def __getattr__(self, name):
        return getattr(_real_os, name)

if not hasattr(_real_os, "path"):
    sys.modules["os"] = _OsCompat()

class _Sha256Compat:
    def __init__(self, data=None):
        self.hash = _real_hashlib.new("sha256")
        if data:
            self.hash.update(data)

    def update(self, data):
        self.hash.update(data)

    def digest(self):
        return self.hash.digest()

    def hexdigest(self):
        return "".join("%02x" % byte for byte in self.hash.digest())

class _HashlibCompat:
    def sha256(self, data=None):
        return _Sha256Compat(data)

    def __getattr__(self, name):
        return getattr(_real_hashlib, name)

if not hasattr(_real_hashlib, "sha256"):
    if not hasattr(_real_hashlib, "new"):
        raise RuntimeError("CircuitPython hashlib has no SHA-256 implementation")
    sys.modules["hashlib"] = _HashlibCompat()

class _DeferredPlanEngine:
    def __init__(self):
        self.module = None

    def __getattr__(self, name):
        if self.module is None:
            del sys.modules["plan_engine"]
            gc.collect()
            self.module = __import__("plan_engine")
            sys.modules["plan_engine"] = self.module
        return getattr(self.module, name)

sys.modules["plan_engine"] = _DeferredPlanEngine()

import live_light_guard as _guard_bundle
# Classroom Studio's complete 21-file export hashes every payload except the
# hash manifest itself. Keep the board verifier aligned with that inventory.
for _name in ("pico-calibration.json", "README-FLASH.md"):
    if _name not in _guard_bundle.HASHED_BUNDLE_FILES:
        _guard_bundle.HASHED_BUNDLE_FILES += (_name,)
_BOOT_BUNDLE = _guard_bundle.load_guard_bundle("/")
del _name, _guard_bundle
gc.collect()

import combined_guard_runtime as runtime
from combined_guard_runtime import main

def _memory_safe_init(self):
    global _BOOT_BUNDLE
    bundle = _BOOT_BUNDLE
    _BOOT_BUNDLE = None
    self.bundle = bundle
    self.guard = runtime.LightStateGuard(
        bundle["states"], bundle["stable_ms"], bundle["hysteresis"],
        bundle["sensor_timeout_ms"])
    self.guard.bundle = bundle
    gc.collect()

    self.arm = runtime.Arm()
    self.keyboard = runtime.Keyboard(runtime.usb_hid.devices)
    self.controls = runtime.Controls(self.arm, self.keyboard)
    self.sensor = runtime.BH1750()
    self.routes = {}
    self.blue = runtime.Button(runtime.board.GP4)
    self.yellow = runtime.Button(runtime.board.GP3)
    self.usb = runtime.usb_cdc.data or runtime.usb_cdc.console
    self.host = bytearray()
    self.calibrating = False
    self.stage = 0
    self.samples = []
    self.sample_started = 0
    self.result = None
    self.saved = False
    self.saved_ids = set()

# The six calibration positions use distinct ascending notes: C4 through A4.
_CAL_NOTES = (262, 294, 330, 349, 392, 440)

def _cal_beep(self, frequency, duration_ms):
    tone = None
    try:
        tone = runtime.pwmio.PWMOut(runtime.board.GP6, duty_cycle=32768,
            frequency=int(frequency), variable_frequency=True)
        runtime.time.sleep(duration_ms / 1000)
    except Exception:
        self.emit("ERR|CAL|AUDIO")
    finally:
        if tone is not None:
            try: tone.duty_cycle = 0; tone.deinit()
            except Exception: pass

def _cal_position_tone(self):
    self._cal_beep(_CAL_NOTES[self.stage], 220)

def _cal_stage_complete_tone(self):
    note = _CAL_NOTES[self.stage]
    self._cal_beep(note, 110)
    runtime.time.sleep(.06)
    self._cal_beep(note, 190)

def _cal_save_success_tone(self):
    self._cal_beep(880, 90)
    runtime.time.sleep(.05)
    self._cal_beep(1320, 180)

def _cal_complete_melody(self):
    for note in _CAL_NOTES:
        self._cal_beep(note, 90)
        runtime.time.sleep(.035)

_original_start_cal = runtime.Combined.start_cal
_original_next_cal = runtime.Combined.next_cal
_original_cal_tick = runtime.Combined.cal_tick
_original_save_cal = runtime.Combined.save_cal

def _audible_start_cal(self):
    _original_start_cal(self)
    if self.calibrating and self.stage == 0:
        self.cal_position_tone()

def _audible_next_cal(self):
    previous = self.stage
    can_wrap = (self.calibrating and
        self.stage == len(runtime.PROFILES) - 1 and
        self.result != "sampling" and
        not (self.result is not None and not self.saved))
    if can_wrap:
        self.stage = 0
        self.result = None
        self.saved = False
        self.emit("EVT|CAL|mode=ready|stage=1|id=" + runtime.PROFILES[0] +
            "|seconds=5|saved=%d" % len(self.saved_ids))
    else:
        _original_next_cal(self)
    if self.calibrating and self.stage != previous:
        self.cal_position_tone()

def _audible_cal_tick(self):
    was_sampling = self.result == "sampling"
    _original_cal_tick(self)
    if was_sampling and isinstance(self.result, dict):
        self.cal_stage_complete_tone()

def _audible_save_cal(self):
    saved_before = len(self.saved_ids)
    _original_save_cal(self)
    saved_after = len(self.saved_ids)
    if saved_after == saved_before + 1:
        if saved_after == len(runtime.PROFILES):
            self.cal_complete_melody()
        else:
            self.cal_save_success_tone()

# Live Classroom Studio commands that execute entirely on the Pico must not
# depend on an attached Pro Micro arm. SCREEN/SETRES is metadata; BEEP drives
# the passive piezo on GP6 directly.
def _live_host_beep(self, frequency, duration_ms):
    tone = None
    try:
        tone = runtime.pwmio.PWMOut(runtime.board.GP6, duty_cycle=32768,
            frequency=int(frequency), variable_frequency=True)
        runtime.time.sleep(duration_ms / 1000)
    finally:
        if tone is not None:
            try: tone.duty_cycle = 0; tone.deinit()
            except Exception: pass

def _live_host_poll(self):
    if self.usb.in_waiting:
        self.host.extend(self.usb.read(self.usb.in_waiting))
    while b"\n" in self.host:
        raw, self.host = self.host.split(b"\n", 1)
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        head = line.split("|", 1)[0]
        try:
            if line == "PING":
                reply = "OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6|role=brain"
            elif line == "CALGET":
                reply = self.calget()
            elif line.startswith("CALSET|"):
                reply = self.calset(line)
            elif line == "GUARD|ON":
                self.controls.start(); reply = "OK|GUARD|ON"
            elif line in ("GUARD|OFF", "HALT"):
                self.controls.stop(); reply = "OK|GUARD|OFF"
            elif line == "LUX?":
                reply = "OK|LUX|lux=%.1f|sensor=ok" % self.sensor.lux()
            elif line.startswith("SETRES|"):
                fields = line.split("|", 1)[1].split(",")
                if len(fields) != 2:
                    raise ValueError("SETRES needs width,height")
                width, height = int(fields[0]), int(fields[1])
                if width < 1 or height < 1:
                    raise ValueError("SETRES dimensions")
                self.host_screen = (width, height)
                reply = "OK|SETRES"
            elif line.startswith("BEEP|"):
                fields = line.split("|", 1)[1].split(",")
                if len(fields) != 2:
                    raise ValueError("BEEP needs frequency,duration")
                frequency, duration_ms = int(fields[0]), int(fields[1])
                if not 30 <= frequency <= 20000 or not 0 <= duration_ms <= 60000:
                    raise ValueError("BEEP range")
                self._live_host_beep(frequency, duration_ms)
                reply = "OK|BEEP"
            else:
                reply = "ERR|UNKNOWN|" + head
        except Exception:
            reply = "ERR|EXEC|" + head
        self.emit(reply)

runtime.Combined.__init__ = _memory_safe_init
runtime.Combined._live_host_beep = _live_host_beep
runtime.Combined.host_poll = _live_host_poll
runtime.Combined._cal_beep = _cal_beep
runtime.Combined.cal_position_tone = _cal_position_tone
runtime.Combined.cal_stage_complete_tone = _cal_stage_complete_tone
runtime.Combined.cal_save_success_tone = _cal_save_success_tone
runtime.Combined.cal_complete_melody = _cal_complete_melody
runtime.Combined.start_cal = _audible_start_cal
runtime.Combined.next_cal = _audible_next_cal
runtime.Combined.cal_tick = _audible_cal_tick
runtime.Combined.save_cal = _audible_save_cal
main()
