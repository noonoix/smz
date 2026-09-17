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
from combined_guard_runtime import main

main()
