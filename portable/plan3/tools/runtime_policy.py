"""Configurable policy helpers for PLAN|2 auto-resume, restart, and buzzer audio."""

import random

DEFAULT_RESTART_MINUTES = (110, 130)
DEFAULT_RESUME_MINUTES = (3, 5)
ALLOWED_BUZZER_PINS = ("GP5", "GP6")

# Windows 11 English: Win+X -> Up -> Up -> Enter -> Up -> Enter.
# (vk, hold range ms, delay-after range ms)
_RESTART_STEPS = (
    (91, (55, 105), (25, 60)),
    (88, (45, 95), (450, 850)),
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
    """User-customizable values shared by UI, exporters and the Pico runtime."""

    def __init__(self, restart_min_minutes=110, restart_max_minutes=130,
                 resume_min_minutes=3, resume_max_minutes=5,
                 auto_resume=True, buzzer_pin="GP5"):
        self.restart_min_seconds, self.restart_max_seconds = minutes_to_seconds_range(
            restart_min_minutes, restart_max_minutes, "restart")
        self.resume_min_seconds, self.resume_max_seconds = minutes_to_seconds_range(
            resume_min_minutes, resume_max_minutes, "auto-resume")
        self.auto_resume = bool(auto_resume)
        pin = str(buzzer_pin).upper()
        if pin not in ALLOWED_BUZZER_PINS:
            raise ValueError("buzzer pin must be GP5 or GP6")
        self.buzzer_pin = pin

    @classmethod
    def from_settings(cls, settings):
        """Read app-style names; absent values preserve safe factory defaults."""
        s = settings or {}
        return cls(
            s.get("RestartMinMinutes", 110), s.get("RestartMaxMinutes", 130),
            s.get("AutoResumeMinMinutes", 3), s.get("AutoResumeMaxMinutes", 5),
            s.get("AutoResumeEnabled", True), s.get("BuzzerPin", "GP5"))

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
    """One Start rolls one restart deadline and, when armed, one resume delay."""

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


def restart_plan_lines():
    """Humanized restart tail; every key has independent down/hold/up timing."""
    lines = ["# restart: Win+X > Up > Up > Enter > Up > Enter"]
    for vk, hold, after in _RESTART_STEPS:
        lines.extend(("KDOWN|%d" % vk, "DELAY|%d,%d" % hold, "KUP|%d" % vk))
        if after is not None:
            lines.append("DELAY|%d,%d" % after)
    return lines


def portable_audio_line(mode, frequency_hz=880, duration_ms=120, buzzer_pin="GP5"):
    """Portable sound is BEEP only; the firmware routes it to selected GP5/GP6."""
    if mode != "deviceBuzzer":
        raise ValueError("portable audio is limited to deviceBuzzer/BEEP")
    pin = str(buzzer_pin).upper()
    if pin not in ALLOWED_BUZZER_PINS:
        raise ValueError("buzzer pin must be GP5 or GP6")
    freq, duration = int(frequency_hz), int(duration_ms)
    if not 30 <= freq <= 20000:
        raise ValueError("buzzer frequency must be 30..20000 Hz")
    if duration < 0:
        raise ValueError("buzzer duration must be non-negative")
    return "BEEP|%d,%d" % (freq, duration)
