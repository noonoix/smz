"""Root cycle state shared by the portable PLAN adapter."""
import os
import random
import time

ARMED_TEXT = "AUTO_RESUME_ARMED"
_ARMED_BYTES = ARMED_TEXT.encode("ascii")

try:
    import microcontroller
    _NVM = microcontroller.nvm
except Exception:
    _NVM = None


class PlanDeadline(Exception):
    pass


class ResumeArmStore:
    """NVM on real Pico; file fallback in simulation/desktop Python."""
    def __init__(self, path=".auto_resume_armed"):
        self.path = path

    def _nvm_available(self):
        return _NVM is not None and len(_NVM) >= len(_ARMED_BYTES) + 1

    def arm(self):
        if self._nvm_available():
            _NVM[0:len(_ARMED_BYTES)] = _ARMED_BYTES
            _NVM[len(_ARMED_BYTES)] = 0xA5
            return
        with open(self.path, "w") as fh:
            fh.write(ARMED_TEXT)

    def is_armed(self):
        if self._nvm_available():
            try:
                return bytes(_NVM[0:len(_ARMED_BYTES)]) == _ARMED_BYTES and _NVM[len(_ARMED_BYTES)] == 0xA5
            except Exception:
                return False
        try:
            with open(self.path, "r") as fh:
                return fh.read().strip() == ARMED_TEXT
        except OSError:
            return False

    def consume(self):
        armed = self.is_armed()
        if armed:
            self.clear()
        return armed

    def clear(self):
        if self._nvm_available():
            try:
                for index in range(len(_ARMED_BYTES) + 1):
                    _NVM[index] = 0
            except Exception:
                pass
            return
        try:
            os.remove(self.path)
        except OSError:
            try:
                with open(self.path, "w") as fh:
                    fh.write("")
            except OSError:
                pass


class RootCycle:
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

    def configure(self, run_min_seconds, run_max_seconds, auto_resume_enabled, resume_min_seconds, resume_max_seconds):
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
        if not self.arm_store.consume() or not self.auto_resume_enabled:
            return None
        if self.resume_delay_seconds is None:
            self.resume_delay_seconds = self.rng.randint(self.resume_range[0], self.resume_range[1])
        return self.resume_delay_seconds
