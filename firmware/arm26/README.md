# Pro Micro firmware 2.6.1

Reports `EVT|HOSTUSB|DOWN/SUSPEND/UP` on private Serial1. The current state is re-announced every 2 seconds so a slower-booting Pico cannot miss the initial event. Identical heartbeats are deduplicated by Pico. Arduino 1.8.x-compatible `uint8_t` state values are used instead of a custom enum in function signatures.
