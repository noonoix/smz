#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path
base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import cycle_runtime as cr

with tempfile.TemporaryDirectory() as td:
    path = os.path.join(td, "armed")
    store = cr.ResumeArmStore(path)
    assert not store.is_armed()
    store.arm()
    assert store.is_armed()
    assert store.consume() is True
    assert not store.is_armed()
    assert store.consume() is False
    store.arm(); store.clear()
    assert not store.is_armed()

class FakeNvm(bytearray): pass
old = cr._NVM
try:
    cr._NVM = FakeNvm(64)
    store = cr.ResumeArmStore("unused")
    store.arm()
    assert store.is_armed()
    assert store.consume() is True
    assert not store.is_armed()
    assert all(value == 0 for value in cr._NVM[:len(cr._ARMED_BYTES) + 1])
finally:
    cr._NVM = old

assert (base / "CIRCUITPY/cycle_runtime.py").read_bytes() == (base / "CIRCUITPY-SPLIT/cycle_runtime.py").read_bytes()
print("resume arm store: 14 passed, 0 failed")
