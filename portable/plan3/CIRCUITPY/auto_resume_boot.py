"""One-shot USB reconnect/boot-settle controller for an armed automatic cycle."""
import random

IDLE = 0
WAIT_FOR_HOST = 1
BOOT_SETTLE = 2
AUTO_START = 3


class AutoResumeBoot:
    def __init__(self, store, now, usb_ready, start_root, cancel_pressed=None, rng=None):
        self.store = store
        self.now = now
        self.usb_ready = usb_ready
        self.start_root = start_root
        self.cancel_pressed = cancel_pressed or (lambda: False)
        self.rng = rng or random
        self.state = WAIT_FOR_HOST if store.is_armed() else IDLE
        self.ready_since = None
        self.start_at = None
        self.resume_range = (180, 300)

    def configure(self, enabled, minimum_seconds, maximum_seconds):
        lo, hi = int(minimum_seconds), int(maximum_seconds)
        if hi < lo:
            lo, hi = hi, lo
        self.resume_range = (max(0, lo), max(0, hi))
        if not enabled and self.state != IDLE:
            self.cancel()

    def cancel(self):
        self.store.clear()
        self.state = IDLE
        self.ready_since = None
        self.start_at = None

    def tick(self):
        if self.state == IDLE:
            return IDLE
        if self.cancel_pressed():
            self.cancel()
            return IDLE
        if self.state == WAIT_FOR_HOST:
            if not self.usb_ready():
                return WAIT_FOR_HOST
            self.ready_since = self.now()
            lo, hi = self.resume_range
            delay = lo if hi <= lo else self.rng.randint(lo, hi)
            self.start_at = self.ready_since + delay
            self.state = BOOT_SETTLE
            return self.state
        if self.state == BOOT_SETTLE:
            # A disconnect restarts the full randomized settle window after reconnect.
            if not self.usb_ready():
                self.ready_since = None
                self.start_at = None
                self.state = WAIT_FOR_HOST
                return self.state
            if self.now() < self.start_at:
                return BOOT_SETTLE
            self.state = AUTO_START
        if self.state == AUTO_START:
            try:
                ok = self.start_root()
            except Exception:
                # Keep the marker for a deliberate retry after the next reboot/reconnect.
                self.state = WAIT_FOR_HOST
                self.ready_since = None
                self.start_at = None
                raise
            if ok is False:
                self.state = WAIT_FOR_HOST
                self.ready_since = None
                self.start_at = None
                return self.state
            # Consume only after Root accepted the start request.
            self.store.clear()
            self.state = IDLE
            return IDLE
        return self.state
