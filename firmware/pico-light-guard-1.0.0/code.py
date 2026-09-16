# Combined Phase 7 firmware entry point for the regular Raspberry Pi Pico.
# The runtime is board-owned after CIRCUITPY is disconnected.
from combined_guard_runtime import main

main()
