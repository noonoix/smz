"""Pure policy helpers for the PLAN|2 random wall-clock runtime/restart contract.

This module is intentionally hardware-free so generators and simulators can share one
validated contract before it is embedded into the Pico runtime.
"""

import random

RUNTIME_MIN_SECONDS = 110 * 60
RUNTIME_MAX_SECONDS = 130 * 60
BUZZER_PIN = "GP5"

# Windows 11 English Win+X -> Shut down or sign out -> Restart.
# Every physical key has independent down/hold/up timing. DELAY ranges are rerolled
# by the PLAN engine every time the sequence runs.
_RESTART_STEPS = (
    (91, (55, 105), (25, 60)),   # Win
    (88, (45, 95), (450, 850)),  # X, then wait for Win+X menu
    (38, (45, 100), (110, 240)), # Up
    (38, (45, 100), (180, 360)), # Up
    (13, (55, 120), (280, 520)), # Enter, open Power submenu
    (38, (45, 100), (350, 700)), # Up to Restart
    (13, (55, 120), None),       # final Enter
)


def normalize_runtime_range(min_seconds=RUNTIME_MIN_SECONDS, max_seconds=RUNTIME_MAX_SECONDS):
    """Return a positive, swap-tolerant inclusive wall-clock range."""
    lo, hi = int(min_seconds), int(max_seconds)
    if hi < lo:
        lo, hi = hi, lo
    if lo <= 0:
        raise ValueError("runtime range must be positive")
    return lo, hi


class WallClockRuntime:
    """One Start creates exactly one random deadline; pause never extends it."""

    def __init__(self, now, rng=None, min_seconds=RUNTIME_MIN_SECONDS,
                 max_seconds=RUNTIME_MAX_SECONDS):
        lo, hi = normalize_runtime_range(min_seconds, max_seconds)
        self.duration_seconds = (rng or random).randint(lo, hi)
        self.started_at = float(now())
        self.deadline = self.started_at + self.duration_seconds

    def expired(self, now):
        return float(now()) >= self.deadline


def restart_plan_lines():
    """Return the humanized low-footprint restart tail as PLAN|2 lines.

    The caller must first release any tracked keys/buttons. This sequence contains no
    Win+R, command shell, PowerShell, file, task, or RunMRU mutation.
    """
    lines = ["# restart: Win+X > Up > Up > Enter > Up > Enter"]
    for vk, hold, after in _RESTART_STEPS:
        lines.append("KDOWN|%d" % vk)
        lines.append("DELAY|%d,%d" % hold)
        lines.append("KUP|%d" % vk)
        if after is not None:
            lines.append("DELAY|%d,%d" % after)
    return lines


def portable_audio_line(mode, frequency_hz=880, duration_ms=120, output_pin=BUZZER_PIN):
    """Compile portable audio only to the Pico buzzer on GP5.

    MP3/WAV, Windows player macros and output-device selection are deliberately rejected.
    """
    if mode != "deviceBuzzer":
        raise ValueError("portable audio is limited to the Pico buzzer (deviceBuzzer/BEEP)")
    if output_pin != BUZZER_PIN:
        raise ValueError("portable buzzer output is fixed to GP5")
    freq, duration = int(frequency_hz), int(duration_ms)
    if not 30 <= freq <= 20000:
        raise ValueError("buzzer frequency must be 30..20000 Hz")
    if duration < 0:
        raise ValueError("buzzer duration must be non-negative")
    return "BEEP|%d,%d" % (freq, duration)
