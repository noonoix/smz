# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# Parse the Guard bundle on a fresh heap, provide the os.path subset absent on
# CircuitPython, and defer the 57 KB plan engine until route execution.
import gc
import sys
import os as _real_os

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

runtime.Combined.__init__ = _memory_safe_init
main()
