# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# Parse and validate the small Guard bundle on a fresh heap, before importing
# the larger hardware runtime. Defer the 57 KB plan engine until route use.
import gc
import sys

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

from live_light_guard import load_guard_bundle
_BOOT_BUNDLE = load_guard_bundle("/")
del load_guard_bundle
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

runtime.Combined.__init__ = _memory_safe_init
main()
