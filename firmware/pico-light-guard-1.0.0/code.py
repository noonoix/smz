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
    self.blue_stop_consumed = False
    self.blue_start_consumed = False
    self.blue_start_pending = False

# The six calibration positions use distinct ascending notes: C4 through A4.
_CAL_NOTES = (262, 294, 330, 349, 392, 440)
# Board control cues are short rhythmic signatures instead of long continuous tones.
# Each pattern stays near one second and uses 3-6 notes so Start/Stop/Pause/Resume
# remain recognizable without sounding like a stuck alarm.
_GUARD_START_PATTERN = ((784, 160), (988, 160), (1175, 200), (0, 80), (1175, 280))
_GUARD_STOP_PATTERN = ((392, 180), (330, 160), (262, 260), (0, 60), (196, 260))
_GUARD_PAUSE_PATTERN = ((523, 180), (0, 100), (523, 180), (0, 100), (523, 340))
_GUARD_RESUME_PATTERN = ((659, 150), (784, 150), (988, 150), (784, 150), (988, 300))

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

def _cal_record_start_tone(self):
    self._cal_beep(660, 65)

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

def _guard_pattern(self, pattern):
    for frequency, duration_ms in pattern:
        if frequency <= 0:
            runtime.time.sleep(duration_ms / 1000)
        else:
            self._cal_beep(frequency, duration_ms)

def _guard_start_tone(self):
    self._guard_pattern(_GUARD_START_PATTERN)

def _guard_stop_tone(self):
    self._guard_pattern(_GUARD_STOP_PATTERN)

def _guard_pause_tone(self):
    self._guard_pattern(_GUARD_PAUSE_PATTERN)

def _guard_resume_tone(self):
    self._guard_pattern(_GUARD_RESUME_PATTERN)

def _immediate_audible_stop(self):
    # Make Stop audible immediately even when the optional Arduino arm is not
    # replying. Set the fail-safe state and release keyboard first, then play
    # the Stop cue before slower arm cleanup/timeout work.
    self.controls.running = False
    self.controls.paused = False
    self.controls.aborted = True
    try:
        self.keyboard.release_all()
    except Exception:
        pass
    self.guard_stop_tone()
    self.arm.abort()

def _immediate_audible_start(self):
    # Acknowledge Start on the physical press, not on release. Route execution
    # remains gated until the press resolves, so a held blue button can still
    # become the long-hold calibration gesture without executing a route.
    self.guard.reset()
    self.controls.start()
    self.blue_start_pending = True
    self.blue_start_consumed = True
    self.guard_start_tone()

def _enter_calibration_from_pending_start(self):
    # The user held the same blue press that initially cued Start. Cancel the
    # not-yet-routable start state and enter calibration directly, without
    # playing a Stop cue or waiting on optional arm cleanup.
    self.blue_start_pending = False
    self.controls.running = False
    self.controls.paused = False
    self.controls.aborted = True
    try:
        self.keyboard.release_all()
    except Exception:
        pass
    self.calibrating = True
    self.stage = 0
    self.samples = []
    self.sample_started = 0
    self.result = None
    self.saved = False
    self.saved_ids = set()
    self.emit("EVT|CAL|mode=ready|stage=1|id=" + runtime.PROFILES[0] + "|seconds=5|saved=0")
    self.cal_position_tone()

_original_start_cal = runtime.Combined.start_cal
_original_next_cal = runtime.Combined.next_cal
_original_cal_tick = runtime.Combined.cal_tick
_original_save_cal = runtime.Combined.save_cal
_original_yellow_action = runtime.Combined.yellow_action

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
    profile_was_saved = runtime.PROFILES[self.stage] in self.saved_ids
    had_pending_result = isinstance(self.result, dict) and not self.saved
    _original_save_cal(self)
    if had_pending_result and self.saved:
        if not profile_was_saved and len(self.saved_ids) == len(runtime.PROFILES):
            self.cal_complete_melody()
        else:
            self.cal_save_success_tone()

def _repeatable_yellow_action(self):
    # Handle both first samples and same-position retries explicitly. A saved
    # value remains active during a retry and is replaced only after the fresh
    # result completes and the user presses yellow again to save it.
    if not self.calibrating:
        was_paused = self.controls.paused
        _original_yellow_action(self)
        if self.controls.running and self.controls.paused != was_paused:
            self.guard_pause_tone() if self.controls.paused else self.guard_resume_tone()
        return
    if self.result == "sampling":
        _original_yellow_action(self)
        return
    if isinstance(self.result, dict) and not self.saved:
        self.save_cal()
        return
    retry = 1 if self.saved and isinstance(self.result, dict) else 0
    self.samples = []
    self.sample_started = runtime.time.monotonic()
    self.result = "sampling"
    self.emit("EVT|CAL|mode=started|stage=%d|id=%s|seconds=5|saved=%d|retry=%d" %
        (self.stage + 1, runtime.PROFILES[self.stage], len(self.saved_ids), retry))
    self.cal_record_start_tone()

def _audible_buttons(self):
    now = runtime.time.monotonic()
    blue = self.blue.poll(now)
    yellow = self.yellow.poll(now)
    if blue == "down" and not self.calibrating and self.controls.running:
        # Stop is fail-safe and should acknowledge immediately on press. This
        # consumes the blue press so the later release/long-hold path cannot
        # re-start the Guard or enter calibration accidentally.
        self.blue_stop_consumed = True
        self.immediate_audible_stop()
    elif blue == "down" and not self.calibrating and not self.controls.running:
        # Start must also acknowledge on the first physical press. Keep route
        # execution pending until release so the same press can still become
        # the long-hold calibration gesture safely.
        self.immediate_audible_start()
    elif blue == "long":
        if self.blue_stop_consumed:
            pass
        elif getattr(self, "blue_start_pending", False):
            self.blue_start_consumed = True
            self.enter_calibration_from_pending_start()
        else:
            self.end_cal() if self.calibrating else self.start_cal()
    elif blue == "up":
        stop_consumed = self.blue_stop_consumed
        start_consumed = getattr(self, "blue_start_consumed", False)
        self.blue_stop_consumed = False
        self.blue_start_consumed = False
        if getattr(self, "blue_start_pending", False):
            self.blue_start_pending = False
        if not stop_consumed and not start_consumed and not self.blue.long:
            if self.calibrating:
                self.next_cal()
    if yellow == "up" and not self.yellow.long:
        self.yellow_action()
    self.cal_tick()


def _audible_loop(self):
    self.emit("combined-pico-guard-executor|GP4 start/stop hold3s=calibration|GP3 pause/resume|GP6 piezo")
    last = 0
    while True:
        self.host_poll()
        self.buttons()
        self.arm.pump()
        if (self.controls.running and not self.calibrating and
                not getattr(self, "blue_start_pending", False) and
                runtime.time.monotonic() - last >= .25):
            last = runtime.time.monotonic()
            try:
                self.guard.update(self.sensor.lux(), int(last * 1000))
                if self.guard.last_decision is not None:
                    self.route(self.guard.last_decision)
            except Exception as exc:
                self.immediate_audible_stop()
                self.emit("ERR|GUARD|FAIL|" + str(exc)[:60])
        runtime.time.sleep(.01)


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
                self.controls.start()
                self.guard_start_tone()
                reply = "OK|GUARD|ON"
            elif line in ("GUARD|OFF", "HALT"):
                self.immediate_audible_stop()
                reply = "OK|GUARD|OFF"
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
runtime.Combined.cal_record_start_tone = _cal_record_start_tone
runtime.Combined.cal_stage_complete_tone = _cal_stage_complete_tone
runtime.Combined.cal_save_success_tone = _cal_save_success_tone
runtime.Combined.cal_complete_melody = _cal_complete_melody
runtime.Combined._guard_pattern = _guard_pattern
runtime.Combined.guard_start_tone = _guard_start_tone
runtime.Combined.guard_stop_tone = _guard_stop_tone
runtime.Combined.guard_pause_tone = _guard_pause_tone
runtime.Combined.guard_resume_tone = _guard_resume_tone
runtime.Combined.immediate_audible_stop = _immediate_audible_stop
runtime.Combined.immediate_audible_start = _immediate_audible_start
runtime.Combined.enter_calibration_from_pending_start = _enter_calibration_from_pending_start
runtime.Combined.start_cal = _audible_start_cal
runtime.Combined.next_cal = _audible_next_cal
runtime.Combined.cal_tick = _audible_cal_tick
runtime.Combined.save_cal = _audible_save_cal
runtime.Combined.yellow_action = _repeatable_yellow_action
runtime.Combined.buttons = _audible_buttons
runtime.Combined.loop = _audible_loop
main()
