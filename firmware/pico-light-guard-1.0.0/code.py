# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# Load the large plan engine first, on a compact freshly collected heap. The
# combined runtime imports it again from sys.modules without the fragmented
# 3 KB allocation that previously failed during board startup.
import gc

gc.collect()
import plan_engine

gc.collect()
from combined_guard_runtime import main

main()
