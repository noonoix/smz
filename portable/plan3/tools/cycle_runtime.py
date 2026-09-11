"""Root-scoped automatic-cycle state machine for PLAN v0.9.67.

Pure Python/CircuitPython-compatible logic. The canonical engine will call `gate()`
inside sleeps, typing, movement, sensor waits, packages, parallel branches and
INCLUDEs. Only the root runner catches PlanDeadline.
"""

import os
import random
import time

ARMED_TEXT = "AUTO_RESUME_ARMED"


class PlanDeadline(Exception):
    """Natural wall-clock expiry. Never use this for Stop, errors or normal aborts."""


class ResumeArmStore:
    """Small one-shot marker persisted on CIRCUITPY across the Windows reboot."""

    def __init__(self, path=".auto_resume_armed"):
        self.path = path

    def arm(self):
        with open(self.path, "w") as fh:
            fh.write(ARMED_TEXT)

    def consume(self):
        try:
            with open(self.path, "r") as fh:
                armed = fh.read().strip() == ARMED_TEXT
        except OSError:
            return False
        try:
            os.remove(self.path)
        except OSError:
            # Fail closed: an unremovable marker must not cause restart loops.
            try:
                with open(self.path, "w") as fh:
                    fh.write("")
            except OSError:
                pass
            return False
        return armed

    def clear(self):
        try:
            os.remove(self.path)
        except OSError:
            pass


class RootCycle:
    """One root Start owns one deadline shared by all nested execution."""

    def __init__(self, now=None, rng=None, arm_store=None):
        self.now = now or time.monotonic
        self.rng = rng or random
        self.arm_store = arm_store or ResumeArmStore()
        self.started_at = None
        self.deadline = None
        self.runtime_seconds = None
        self.auto_resume_enabled = False
        self.resume_range = (180, 300)
        self.resume_delay_seconds = None
        self.stopped = False
        self.failed = False
        self.expired_naturally = False
        self.restart_started = False

    @staticmethod
    def _positive_range(lo, hi, name):
        lo, hi = int(lo), int(hi)
        if hi < lo:
            lo, hi = hi, lo
        if lo <= 0:
            raise ValueError(name + " range must be positive")
        return lo, hi

    def configure(self, run_min_seconds, run_max_seconds,
                  auto_resume_enabled, resume_min_seconds, resume_max_seconds):
        if self.started_at is not None:
            raise RuntimeError("cycle already started")
        self.run_range = self._positive_range(run_min_seconds, run_max_seconds, "RUNFOR")
        self.resume_range = self._positive_range(resume_min_seconds, resume_max_seconds, "AUTORESUME")
        self.auto_resume_enabled = bool(auto_resume_enabled)

    def start(self):
        if self.started_at is not None:
            return self.runtime_seconds
        if not hasattr(self, "run_range"):
            raise RuntimeError("RUNFOR is not configured")
        self.started_at = float(self.now())
        self.runtime_seconds = self.rng.randint(self.run_range[0], self.run_range[1])
        self.deadline = self.started_at + self.runtime_seconds
        return self.runtime_seconds

    def gate(self):
        """Call frequently. Pause intentionally does not alter this wall-clock deadline."""
        if self.stopped:
            raise RuntimeError("cycle stopped")
        if self.failed:
            raise RuntimeError("cycle failed")
        if self.deadline is not None and float(self.now()) >= self.deadline:
            self.expired_naturally = True
            raise PlanDeadline()

    def stop(self):
        self.stopped = True
        self.arm_store.clear()

    def fail(self):
        self.failed = True
        self.arm_store.clear()

    def arm_natural_restart(self, release_all):
        """Root catch path only: release first, persist marker second, restart once."""
        if not self.expired_naturally or self.stopped or self.failed or self.restart_started:
            return False
        release_all()
        if self.auto_resume_enabled:
            self.arm_store.arm()
        else:
            self.arm_store.clear()
        self.restart_started = True
        return True

    def consume_resume_on_boot(self):
        """Manual boot returns None; an armed boot returns one freshly-drawn delay."""
        if not self.arm_store.consume():
            return None
        if not self.auto_resume_enabled:
            return None
        if self.resume_delay_seconds is None:
            self.resume_delay_seconds = self.rng.randint(self.resume_range[0], self.resume_range[1])
        return self.resume_delay_seconds
