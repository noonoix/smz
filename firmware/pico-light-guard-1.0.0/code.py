# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# Keep the 57 KB plan engine out of the boot/control-plane heap. It is loaded
# only when a route actually asks for an executor symbol.
import gc
import sys

class _DeferredPlanEngine:
    def __init__(self):
        self.module = None

    def __getattr__(self, name):
        if self.module is None:
            # Remove the proxy during the real import to avoid resolving back to
            # ourselves, compact the heap, then cache the resulting module.
            del sys.modules["plan_engine"]
            gc.collect()
            self.module = __import__("plan_engine")
            sys.modules["plan_engine"] = self.module
        return getattr(self.module, name)

sys.modules["plan_engine"] = _DeferredPlanEngine()
import combined_guard_runtime as runtime

def _memory_safe_init(self):
    # Validate and parse the bundle before allocating UART, HID, I2C and GPIO
    # objects. Reuse the parsed bundle instead of loading both JSON files twice.
    bundle = runtime.load_guard_bundle("/")
    guard = runtime.LightStateGuard(
        bundle["states"], bundle["stable_ms"], bundle["hysteresis"],
        bundle["sensor_timeout_ms"])
    guard.bundle = bundle
    self.bundle = bundle
    self.guard = guard
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
runtime.main()
