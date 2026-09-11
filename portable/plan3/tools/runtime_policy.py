"""Configurable policy helpers for PLAN|2 auto-resume, restart, and buzzer audio."""

import random

DEFAULT_RESTART_MINUTES = (110, 130)
DEFAULT_RESUME_MINUTES = (3, 5)
BUZZER_PIN = "GP6"

# Keys after Win+X: Up, Up, Enter, Up, Enter.
_RESTART_MENU_STEPS = (
    (38, (45, 100), (110, 240)),
    (38, (45, 100), (180, 360)),
    (13, (55, 120), (280, 520)),
    (38, (45, 100), (350, 700)),
    (13, (55, 120), None),
)


def _positive_pair(mn, mx, name):
    lo, hi = int(mn), int(mx)
    if hi < lo:
        lo, hi = hi, lo
    if lo <= 0:
        raise ValueError(name + " range must be positive")
    return lo, hi


def minutes_to_seconds_range(mn, mx, name="time"):
    lo, hi = _positive_pair(mn, mx, name)
    return lo * 60, hi * 60


class RuntimeOptions:
    def __init__(self, restart_min_minutes=110, restart_max_minutes=130,
                 resume_min_minutes=3, resume_max_minutes=5,
                 auto_resume=True, buzzer_pin=BUZZER_PIN):
        self.restart_min_seconds, self.restart_max_seconds = minutes_to_seconds_range(
            restart_min_minutes, restart_max_minutes, "restart")
        self.resume_min_seconds, self.resume_max_seconds = minutes_to_seconds_range(
            resume_min_minutes, resume_max_minutes, "auto-resume")
        self.auto_resume = bool(auto_resume)
        pin = str(buzzer_pin).upper()
        if pin != BUZZER_PIN:
            raise ValueError("portable buzzer output is fixed to GP6")
        self.buzzer_pin = pin

    @classmethod
    def from_settings(cls, settings):
        s = settings or {}
        return cls(
            s.get("RestartMinMinutes", 110), s.get("RestartMaxMinutes", 130),
            s.get("AutoResumeMinMinutes", 3), s.get("AutoResumeMaxMinutes", 5),
            s.get("AutoResumeEnabled", True), s.get("BuzzerPin", BUZZER_PIN))

    def as_settings(self):
        return {
            "RestartMinMinutes": self.restart_min_seconds // 60,
            "RestartMaxMinutes": self.restart_max_seconds // 60,
            "AutoResumeMinMinutes": self.resume_min_seconds // 60,
            "AutoResumeMaxMinutes": self.resume_max_seconds // 60,
            "AutoResumeEnabled": self.auto_resume,
            "BuzzerPin": self.buzzer_pin,
        }


class AutoCycle:
    def __init__(self, now, options=None, rng=None):
        self.options = options or RuntimeOptions()
        self.rng = rng or random
        self.started_at = float(now())
        self.runtime_seconds = self.rng.randint(
            self.options.restart_min_seconds, self.options.restart_max_seconds)
        self.deadline = self.started_at + self.runtime_seconds
        self.resume_delay_seconds = None

    def expired(self, now):
        return float(now()) >= self.deadline

    def arm_resume(self):
        if not self.options.auto_resume:
            self.resume_delay_seconds = None
            return None
        if self.resume_delay_seconds is None:
            self.resume_delay_seconds = self.rng.randint(
                self.options.resume_min_seconds, self.options.resume_max_seconds)
        return self.resume_delay_seconds


def _tap(lines, vk, hold, after=None):
    lines.extend(("KDOWN|%d" % vk, "DELAY|%d,%d" % hold, "KUP|%d" % vk))
    if after is not None:
        lines.append("DELAY|%d,%d" % after)


def restart_plan_lines():
    """Win is held while X is tapped; every hold/gap is independently ranged."""
    lines = ["# restart: Win+X > Up > Up > Enter > Up > Enter"]
    lines.extend((
        "KDOWN|91",
        "DELAY|25,60",
        "KDOWN|88",
        "DELAY|45,95",
        "KUP|88",
        "DELAY|25,60",
        "KUP|91",
        "DELAY|450,850",
    ))
    for vk, hold, after in _RESTART_MENU_STEPS:
        _tap(lines, vk, hold, after)
    return lines


def portable_audio_line(mode, frequency_hz=880, duration_ms=120, buzzer_pin=BUZZER_PIN):
    """Portable sound is BEEP only and firmware output is fixed to GP6."""
    if mode != "deviceBuzzer":
        raise ValueError("portable audio is limited to deviceBuzzer/BEEP")
    pin = str(buzzer_pin).upper()
    if pin != BUZZER_PIN:
        raise ValueError("portable buzzer output is fixed to GP6")
    freq, duration = int(frequency_hz), int(duration_ms)
    if not 30 <= freq <= 20000:
        raise ValueError("buzzer frequency must be 30..20000 Hz")
    if duration < 0:
        raise ValueError("buzzer duration must be non-negative")
    return "BEEP|%d,%d" % (freq, duration)
