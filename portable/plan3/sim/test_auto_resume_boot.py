#!/usr/bin/env python3
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import auto_resume_boot as arb

class Store:
    def __init__(self, armed=True): self.armed = armed; self.clears = 0
    def is_armed(self): return self.armed
    def clear(self): self.armed = False; self.clears += 1

class Rng:
    def __init__(self): self.calls = []
    def randint(self, lo, hi): self.calls.append((lo, hi)); return 240

now = [10.0]
ready = [False]
starts = []
store, rng = Store(), Rng()
boot = arb.AutoResumeBoot(store, lambda: now[0], lambda: ready[0], lambda: starts.append(now[0]) or True, rng=rng)
assert boot.state == arb.WAIT_FOR_HOST
assert boot.tick() == arb.WAIT_FOR_HOST and rng.calls == []
ready[0] = True
assert boot.tick() == arb.BOOT_SETTLE
assert rng.calls == [(180, 300)] and boot.start_at == 250.0
now[0] = 249.9
assert boot.tick() == arb.BOOT_SETTLE and starts == []
now[0] = 250.0
assert boot.tick() == arb.IDLE and starts == [250.0]
assert store.clears == 1

# Disconnect restarts settling and makes one fresh draw per stable connection.
now[0], ready[0] = 0.0, True
store, rng = Store(), Rng()
boot = arb.AutoResumeBoot(store, lambda: now[0], lambda: ready[0], lambda: True, rng=rng)
boot.tick(); ready[0] = False
assert boot.tick() == arb.WAIT_FOR_HOST
ready[0] = True; now[0] = 5.0
boot.tick()
assert rng.calls == [(180, 300), (180, 300)]

# User cancel and disabled policy clear the one-shot marker.
store = Store(); cancelled = [True]
boot = arb.AutoResumeBoot(store, lambda: 0, lambda: True, lambda: True, lambda: cancelled[0])
assert boot.tick() == arb.IDLE and store.clears == 1
store = Store(); boot = arb.AutoResumeBoot(store, lambda: 0, lambda: True, lambda: True)
boot.configure(False, 300, 180)
assert boot.state == arb.IDLE and store.clears == 1

# Failed start keeps marker armed for a future reconnect/reboot.
store = Store(); ready[0] = True; now[0] = 0
boot = arb.AutoResumeBoot(store, lambda: now[0], lambda: ready[0], lambda: False)
boot.configure(True, 0, 0)
boot.tick()
assert boot.tick() == arb.WAIT_FOR_HOST and store.armed and store.clears == 0

assert (base / "CIRCUITPY/auto_resume_boot.py").read_bytes() == (base / "CIRCUITPY-SPLIT/auto_resume_boot.py").read_bytes()
print("auto resume boot: 21 passed, 0 failed")
