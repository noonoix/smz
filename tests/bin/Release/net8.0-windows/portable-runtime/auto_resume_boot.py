"""One-shot, helper-free USB/HID reconnect controller for an armed cycle.

Primary signal: Pro Micro HOSTUSB events forwarded by the Pico. Fallback signal:
Pico supervisor.runtime.usb_connected. A late-armed cycle must observe DOWN or
SUSPEND before UP; an armed marker present at Pico boot already proves a reboot.
"""
import random

IDLE = 0
WAIT_FOR_HOST = 1
BOOT_SETTLE = 2
AUTO_START = 3


class AutoResumeBoot:
    def __init__(self, store, now, usb_ready, start_root, cancel_pressed=None,
                 rng=None, usb_down=None, stable_seconds=12):
        self.store = store
        self.now = now
        self.usb_ready = usb_ready
        self.usb_down = usb_down or (lambda: not usb_ready())
        self.start_root = start_root
        self.cancel_pressed = cancel_pressed or (lambda: False)
        self.rng = rng or random
        armed_at_boot = store.is_armed()
        self.state = WAIT_FOR_HOST if armed_at_boot else IDLE
        self.disconnect_seen = bool(armed_at_boot)
        self.ready_since = None
        self.start_at = None
        self.resume_range = (180, 300)
        self.stable_seconds = max(0, int(stable_seconds))

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
        self.disconnect_seen = False
        self.ready_since = None
        self.start_at = None

    def _back_to_wait(self, disconnected=False):
        self.ready_since = None
        self.start_at = None
        self.state = WAIT_FOR_HOST
        if disconnected:
            self.disconnect_seen = True
        return self.state

    def tick(self):
        # A marker armed after construction means the same Pico stayed powered. It
        # must observe a real USB/HID DOWN/SUSPEND before accepting the next UP.
        if self.state == IDLE:
            if not self.store.is_armed():
                return IDLE
            self.state = WAIT_FOR_HOST
            self.disconnect_seen = False
        if self.cancel_pressed():
            self.cancel()
            return IDLE

        down = bool(self.usb_down())
        ready = bool(self.usb_ready())
        if self.state == WAIT_FOR_HOST:
            if down:
                self.disconnect_seen = True
                return WAIT_FOR_HOST
            if not self.disconnect_seen or not ready:
                return WAIT_FOR_HOST
            self.ready_since = self.now()
            lo, hi = self.resume_range
            delay = lo if hi <= lo else self.rng.randint(lo, hi)
            self.start_at = self.ready_since + self.stable_seconds + delay
            self.state = BOOT_SETTLE
            return self.state

        if self.state == BOOT_SETTLE:
            if down or not ready:
                return self._back_to_wait(disconnected=down)
            if self.now() < self.start_at:
                return BOOT_SETTLE
            self.state = AUTO_START

        if self.state == AUTO_START:
            try:
                ok = self.start_root()
            except Exception:
                self._back_to_wait()
                raise
            if ok is False:
                return self._back_to_wait()
            self.store.clear()
            self.state = IDLE
            self.disconnect_seen = False
            return IDLE
        return self.state
