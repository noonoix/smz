#!/usr/bin/env python3
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import restart_windows as rw

class Rng:
    def __init__(self): self.draws = []
    def randint(self, lo, hi):
        self.draws.append((lo, hi))
        return lo + (hi - lo) // 2

class Ctx:
    def __init__(self): self.events = []
    def kdown(self, vk): self.events.append(("down", vk))
    def kup(self, vk): self.events.append(("up", vk))
    def sleep_ms(self, ms): self.events.append(("sleep", ms)); return True

ctx = Ctx(); rng = Rng(); rw.perform(ctx, rng)
keys = [e for e in ctx.events if e[0] != "sleep"]
assert keys == [
    ("down", 91), ("down", 88), ("up", 88), ("up", 91),
    ("down", 38), ("up", 38), ("down", 38), ("up", 38),
    ("down", 13), ("up", 13), ("down", 38), ("up", 38),
    ("down", 13), ("up", 13),
]
assert keys.index(("up", 88)) < keys.index(("up", 91))
assert rng.draws == [
    (25, 60), (45, 95), (25, 60), (450, 850),
    (45, 100), (110, 240), (45, 100), (180, 360),
    (55, 120), (280, 520), (45, 100), (350, 700), (55, 120),
]
assert (base / "CIRCUITPY/restart_windows.py").read_bytes() == (base / "CIRCUITPY-SPLIT/restart_windows.py").read_bytes()
print("restart windows executor: 16 passed, 0 failed")
