# Classroom Studio Phase 7 — isolated light Guard firmware
# Version: pico-light-guard 1.0.0
# Hardware: regular Raspberry Pi Pico, BH1750/GY-30, two buttons and passive piezo
# BH1750: SDA=GP20/pin 26, SCL=GP21/pin 27, ADDR=GND/0x23
# Buttons: GP4=blue Start/Stop + 3s calibration enter/exit, GP3=yellow Pass/Save
# Piezo: GP6 PWM
# This firmware intentionally has no HID, UART, keyboard, mouse, macro or actuator path.

import json
import time
import board
import busio
import digitalio
import pwmio
import sys

VERSION = "1.0.0"
ADDR = 0x23
POWER_ON = 0x01
RESET = 0x07
CONT_HIRES = 0x10
BUTTON_DEBOUNCE = 0.04
CAL_SECONDS = 5.0
CAL_SAMPLE_SECONDS = 0.12
CAL_MAX_SPREAD = 5.0
PROFILE_PATH = "/guard-calibration.json"

PROFILE_IDS = (
    "desktop",
    "login-or-dc",
    "character-dashboard",
    "entering-game-loading",
    "game",
    "targeted",
)
NOTE_HZ = (262, 294, 330, 349, 392, 440)

# No default value is treated as calibrated truth. The app is the source of truth;
# CALSET writes the portable local copy after the app has a valid revision.
profiles = {}
calibration_revision = ""

_i2c = None
_sensor = None
_sensor_attempted = False
_sequence = 0
_guard_enabled = False
_guard_candidate = None
guard_candidate_since = None
guard_state = None

_calibrating = False
_cal_stage = 0
_cal_sampling = False
_cal_started = 0.0
_cal_values = []
_cal_stage_result = None
_cal_stage_saved = False
_cal_saved_ids = set()

_tone = None


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def ensure_sensor():
    global _i2c, _sensor, _sensor_attempted
    if _sensor_attempted:
        return _sensor
    _sensor_attempted = True
    try:
        # Deferred initialization keeps PING and button handling available without BH1750.
        _i2c = busio.I2C(board.GP21, board.GP20)
        _sensor = Bh1750(_i2c)
    except Exception:
        _sensor = None
    return _sensor


class Bh1750:
    def __init__(self, i2c):
        self.i2c = i2c
        self.buf = bytearray(2)
        self.write(POWER_ON)
        self.write(RESET)
        self.write(CONT_HIRES)
        time.sleep(0.20)

    def write(self, value):
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
        value = raw / 1.2
        if value != value or value < 0:
            raise RuntimeError("invalid lux")
        return value


def load_calibration():
    global profiles, calibration_revision
    try:
        with open(PROFILE_PATH, "r") as fh:
            payload = json.load(fh)
        revision = payload.get("revision", "")
        loaded = payload.get("profiles", {})
        valid = {}
        for pid in PROFILE_IDS:
            item = loaded.get(pid)
            if not isinstance(item, dict):
                continue
            center = item.get("center")
            tolerance = item.get("tolerance")
            stable_ms = item.get("stable_ms", 750)
            if isinstance(center, (int, float)) and center >= 0 \
                    and isinstance(tolerance, (int, float)) and tolerance >= 0 \
                    and isinstance(stable_ms, (int, float)) and stable_ms >= 0:
                valid[pid] = {
                    "center": float(center),
                    "tolerance": float(tolerance),
                    "stable_ms": int(stable_ms),
                }
        profiles = valid
        calibration_revision = str(revision)
    except Exception:
        profiles = {}
        calibration_revision = ""


def save_calibration():
    payload = {
        "format": 1,
        "revision": calibration_revision,
        "profiles": profiles,
    }
    temporary = PROFILE_PATH + ".tmp"
    with open(temporary, "w") as fh:
        json.dump(payload, fh)
    try:
        import os
        os.remove(PROFILE_PATH)
    except Exception:
        pass
    import os
    os.rename(temporary, PROFILE_PATH)


def beep(frequency, duration_ms):
    global _tone
    try:
        if _tone is not None:
            _tone.deinit()
        _tone = pwmio.PWMOut(
            board.GP6,
            duty_cycle=32768,
            frequency=int(frequency),
            variable_frequency=True,
        )
        time.sleep(max(1, duration_ms) / 1000.0)
    except Exception:
        pass
    finally:
        if _tone is not None:
            try:
                _tone.duty_cycle = 0
                _tone.deinit()
            except Exception:
                pass
            _tone = None


def stage_note(stage):
    beep(NOTE_HZ[stage], 150)


def success_sound():
    for frequency in (NOTE_HZ[0], NOTE_HZ[2], NOTE_HZ[5]):
        beep(frequency, 130)
        time.sleep(0.04)


def error_sound():
    beep(150, 250)


def emit(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def lux_reply():
    global _sequence
    sensor = ensure_sensor()
    if sensor is None:
        return "ERR|NOSENSOR|LUX"
    try:
        value = sensor.read_lux()
        _sequence = (_sequence + 1) & 0xFFFFFFFF
        return "OK|LUX|seq=%d|lux=%.1f|mode=hires|sensor=ok" % (_sequence, value)
    except Exception:
        return "ERR|I2C|LUX"


def profile_match(value, pid):
    item = profiles.get(pid)
    if item is None:
        return False
    return abs(value - item["center"]) <= item["tolerance"]


def guard_sample(value, now):
    global guard_candidate, guard_candidate_since, guard_state
    if not _guard_enabled or _calibrating:
        return
    match = None
    for pid in PROFILE_IDS:
        if profile_match(value, pid):
            if match is not None:
                guard_candidate = None
                guard_candidate_since = None
                if guard_state is not None:
                    guard_state = None
                    emit("EVT|GUARD|state=unknown|reason=ambiguous|lux=%.1f" % value)
                return
            match = pid
    if match is None:
        guard_candidate = None
        guard_candidate_since = None
        if guard_state is not None:
            guard_state = None
            emit("EVT|GUARD|state=unknown|reason=no-match|lux=%.1f" % value)
        return
    if match != guard_candidate:
        guard_candidate = match
        guard_candidate_since = now
        return
    stable_ms = profiles[match]["stable_ms"]
    if guard_state != match and guard_candidate_since is not None \
            and (now - guard_candidate_since) * 1000 >= stable_ms:
        guard_state = match
        emit("EVT|GUARD|state=%s|lux=%.1f|revision=%s" %
             (match, value, calibration_revision))


def start_calibration():
    global _calibrating, _cal_stage, _cal_sampling, _cal_stage_result
    global _cal_stage_saved, _cal_saved_ids
    _calibrating = True
    _cal_stage = 0
    _cal_sampling = False
    _cal_stage_result = None
    _cal_stage_saved = False
    _cal_saved_ids = set()
    stage_note(_cal_stage)
    emit("EVT|CAL|mode=ready|stage=1|id=%s|seconds=5|saved=0" % PROFILE_IDS[_cal_stage])


def reset_calibration_state():
    global _calibrating, _cal_sampling, _cal_values, _cal_stage_result
    global _cal_stage_saved, _cal_saved_ids
    _calibrating = False
    _cal_sampling = False
    _cal_values = []
    _cal_stage_result = None
    _cal_stage_saved = False
    _cal_saved_ids = set()


def cancel_calibration(reason="button"):
    reset_calibration_state()
    error_sound()
    emit("EVT|CAL|mode=cancelled|reason=%s" % reason)


def save_current_calibration_stage():
    global _cal_stage_saved
    if _cal_stage_result is None or _cal_stage_saved:
        return False
    pid = PROFILE_IDS[_cal_stage]
    previous = profiles.get(pid)
    profiles[pid] = dict(_cal_stage_result)
    try:
        # Only a yellow-button save changes the local stored value. A later blue
        # long-hold can therefore exit after fixing one position without touching
        # unsaved stages or discarding the other five positions.
        save_calibration()
    except Exception:
        if previous is None:
            profiles.pop(pid, None)
        else:
            profiles[pid] = previous
        error_sound()
        emit("ERR|CAL|SAVE|stage=%d" % (_cal_stage + 1))
        return False
    _cal_stage_saved = True
    _cal_saved_ids.add(pid)
    emit("EVT|CAL|mode=saved-stage|stage=%d|id=%s|saved=%d" %
         (_cal_stage + 1, pid, len(_cal_saved_ids)))
    if len(_cal_saved_ids) == len(PROFILE_IDS):
        success_sound()
        emit("EVT|CAL|mode=complete-set|count=6|revision=%s" % calibration_revision)
    return True


def advance_calibration_stage():
    global _cal_stage, _cal_stage_result, _cal_stage_saved
    if not _calibrating:
        return
    if _cal_sampling:
        error_sound()
        emit("ERR|CAL|BUSY|stage=%d" % (_cal_stage + 1))
        return
    if _cal_stage_result is not None and not _cal_stage_saved:
        error_sound()
        emit("ERR|CAL|UNSAVED|stage=%d" % (_cal_stage + 1))
        return
    if _cal_stage >= len(PROFILE_IDS) - 1:
        stage_note(_cal_stage)
        emit("EVT|CAL|mode=last|stage=6|id=%s|saved=%d" %
             (PROFILE_IDS[_cal_stage], len(_cal_saved_ids)))
        return
    _cal_stage += 1
    _cal_stage_result = None
    _cal_stage_saved = False
    stage_note(_cal_stage)
    emit("EVT|CAL|mode=ready|stage=%d|id=%s|seconds=5|saved=%d" %
         (_cal_stage + 1, PROFILE_IDS[_cal_stage], len(_cal_saved_ids)))


def finish_calibration():
    if not _calibrating:
        return
    if _cal_sampling:
        error_sound()
        emit("ERR|CAL|BUSY|stage=%d" % (_cal_stage + 1))
        return
    if _cal_stage_result is not None and not _cal_stage_saved:
        error_sound()
        emit("ERR|CAL|UNSAVED|stage=%d" % (_cal_stage + 1))
        return
    try:
        save_calibration()
    except Exception:
        error_sound()
        emit("ERR|CAL|SAVE")
        return
    saved_count = len(_cal_saved_ids)
    reset_calibration_state()
    emit("EVT|CAL|mode=exited|saved=%d" % saved_count)


def begin_or_save_calibration():
    global _cal_sampling, _cal_started, _cal_values
    if not _calibrating:
        return
    if _cal_sampling:
        return
    if _cal_stage_result is None:
        if ensure_sensor() is None:
            error_sound()
            emit("ERR|CAL|NOSENSOR|stage=%d" % (_cal_stage + 1))
            return
        stage_note(_cal_stage)
        _cal_values = []
        _cal_started = time.monotonic()
        _cal_sampling = True
        emit("EVT|CAL|mode=started|stage=%d|id=%s|seconds=5|saved=%d" %
             (_cal_stage + 1, PROFILE_IDS[_cal_stage], len(_cal_saved_ids)))
        return
    if save_current_calibration_stage():
        beep(NOTE_HZ[_cal_stage], 220)


def calibration_tick(now):
    global _cal_sampling, _cal_values, _cal_stage_result
    if not _calibrating or not _cal_sampling:
        return
    sensor = ensure_sensor()
    if sensor is None:
        cancel_calibration("sensor")
        return
    try:
        _cal_values.append(sensor.read_lux())
    except Exception:
        cancel_calibration("i2c")
        return
    if now - _cal_started < CAL_SECONDS:
        time.sleep(CAL_SAMPLE_SECONDS)
        return
    if len(_cal_values) < 5:
        _cal_sampling = False
        error_sound()
        emit("ERR|CAL|TOO_FEW|stage=%d" % (_cal_stage + 1))
        return
    center = median(_cal_values)
    spread = max(_cal_values) - min(_cal_values)
    _cal_sampling = False
    if spread > CAL_MAX_SPREAD:
        _cal_values = []
        error_sound()
        emit("ERR|CAL|UNSTABLE|stage=%d|median=%.1f|spread=%.1f" %
             (_cal_stage + 1, center, spread))
        return
    _cal_stage_result = {
        "center": float(center),
        "tolerance": max(2.0, spread * 1.5),
        "stable_ms": 750,
    }
    _cal_stage_saved = False
    beep(NOTE_HZ[_cal_stage], 220)
    emit("EVT|CAL|mode=complete-stage|stage=%d|id=%s|center=%.1f|spread=%.1f|tolerance=%.1f|saved=0" %
         (_cal_stage + 1, PROFILE_IDS[_cal_stage], center, spread,
          _cal_stage_result["tolerance"]))
    _cal_values = []


def parse_calset(parts):
    global calibration_revision
    if len(parts) != 6:
        return "ERR|CALSET|ARG"
    revision, pid = parts[1], parts[2]
    if pid not in PROFILE_IDS:
        return "ERR|CALSET|PROFILE"
    try:
        center = float(parts[3])
        tolerance = float(parts[4])
        stable_ms = int(parts[5])
        if center < 0 or tolerance < 0 or stable_ms < 0:
            raise ValueError()
    except Exception:
        return "ERR|CALSET|VALUE"
    profiles[pid] = {"center": center, "tolerance": tolerance, "stable_ms": stable_ms}
    calibration_revision = revision[:80]
    try:
        save_calibration()
    except Exception:
        return "ERR|CALSET|SAVE"
    return "OK|CALSET|%s|revision=%s" % (pid, calibration_revision)


def handle(line):
    global _guard_enabled
    if line == "PING":
        return ("OK|PONG|pico-light-guard %s|role=light-guard|hid=off|" \
                "uart=off|actuator=off|sensor=BH1750|button=GP4,GP3|buzzer=GP6|profiles=6") % VERSION
    if line == "LUX?":
        return lux_reply()
    if line == "CALGET":
        return "OK|CALGET|revision=%s|count=%d" % (calibration_revision, len(profiles))
    if line.startswith("CALSET|"):
        return parse_calset(line.split("|"))
    if line == "GUARD|ON":
        _guard_enabled = True
        return "OK|GUARD|ON"
    if line == "GUARD|OFF" or line == "HALT":
        _guard_enabled = False
        return "OK|GUARD|OFF"
    if line == "BYE":
        _guard_enabled = False
        return "OK|BYE"
    return "ERR|GUARD|UNKNOWN|" + line.split("|", 1)[0][:32]


class Button:
    def __init__(self, pin):
        self.io = digitalio.DigitalInOut(pin)
        self.io.direction = digitalio.Direction.INPUT
        self.io.pull = digitalio.Pull.UP
        self.down = False
        self.started = 0.0
        self.long_fired = False
        self.changed = 0.0

    def poll(self, now):
        pressed = not self.io.value
        if pressed != self.down and now - self.changed >= BUTTON_DEBOUNCE:
            self.changed = now
            self.down = pressed
            if pressed:
                self.started = now
                self.long_fired = False
                return "down"
            return "up"
        if pressed and not self.long_fired and now - self.started >= 3.0:
            self.long_fired = True
            return "long"
        return None


start_button = Button(board.GP4)
pass_button = Button(board.GP3)
load_calibration()

emit("pico-light-guard %s | blue GP4=Start/Stop hold3s=calibration enter/exit | yellow GP3=Pass/Save | GP6=piezo" % VERSION)
last_guard_sample = 0.0

while True:
    now = time.monotonic()
    event = start_button.poll(now)
    if event == "long":
        if _calibrating:
            finish_calibration()
        else:
            start_calibration()
    elif event == "up" and not start_button.long_fired:
        if _calibrating:
            advance_calibration_stage()
        else:
            _guard_enabled = not _guard_enabled
            emit("EVT|GUARD|enabled=%s" % ("true" if _guard_enabled else "false"))
            beep(660 if _guard_enabled else 220, 100)

    event = pass_button.poll(now)
    if event == "up" and not pass_button.long_fired:
        begin_or_save_calibration()

    calibration_tick(now)
    if _guard_enabled and not _calibrating and now - last_guard_sample >= 0.25:
        last_guard_sample = now
        sensor = ensure_sensor()
        if sensor is not None:
            try:
                guard_sample(sensor.read_lux(), now)
            except Exception:
                emit("ERR|GUARD|I2C")

    if sys.stdin and getattr(sys.stdin, "in_waiting", 0):
        line = sys.stdin.readline().strip()
        if line:
            emit(handle(line))
    time.sleep(0.01)
