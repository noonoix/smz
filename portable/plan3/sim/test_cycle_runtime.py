#!/usr/bin/env python3
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cycle_runtime import PlanDeadline, ResumeArmStore, RootCycle

class Clock:
    def __init__(self): self.value = 1000.0
    def now(self): return self.value

with tempfile.TemporaryDirectory() as td:
    marker = str(Path(td) / "armed")
    clock = Clock()
    store = ResumeArmStore(marker)
    cycle = RootCycle(clock.now, random.Random(4), store)
    cycle.configure(7800, 6600, True, 300, 180)
    chosen = cycle.start()
    assert 6600 <= chosen <= 7800
    assert cycle.start() == chosen
    clock.value = cycle.deadline - 0.001
    cycle.gate()
    clock.value = cycle.deadline
    try: cycle.gate()
    except PlanDeadline: pass
    else: raise AssertionError("deadline did not interrupt")

    calls = []
    assert cycle.arm_natural_restart(lambda: calls.append("release"))
    assert calls == ["release"] and Path(marker).read_text() == "AUTO_RESUME_ARMED"
    assert not cycle.arm_natural_restart(lambda: calls.append("again"))

    boot = RootCycle(clock.now, random.Random(8), store)
    boot.configure(6600, 7800, True, 180, 300)
    delay = boot.consume_resume_on_boot()
    assert 180 <= delay <= 300
    assert not Path(marker).exists()
    assert boot.consume_resume_on_boot() is None

    manual = RootCycle(clock.now, random.Random(1), ResumeArmStore(marker))
    manual.configure(6600, 7800, True, 180, 300)
    assert manual.consume_resume_on_boot() is None

    stopped = RootCycle(clock.now, random.Random(1), ResumeArmStore(marker))
    stopped.configure(6600, 7800, True, 180, 300)
    stopped.start(); stopped.stop()
    assert not stopped.arm_natural_restart(lambda: calls.append("bad"))
    assert not Path(marker).exists()

    failed = RootCycle(clock.now, random.Random(1), ResumeArmStore(marker))
    failed.configure(6600, 7800, True, 180, 300)
    failed.start(); failed.fail()
    assert not failed.arm_natural_restart(lambda: calls.append("bad"))
    assert not Path(marker).exists()

    no_resume = RootCycle(clock.now, random.Random(1), ResumeArmStore(marker))
    no_resume.configure(1, 1, False, 180, 300)
    no_resume.start(); clock.value = no_resume.deadline
    try: no_resume.gate()
    except PlanDeadline: pass
    assert no_resume.arm_natural_restart(lambda: calls.append("release-no-resume"))
    assert not Path(marker).exists()

print("cycle runtime state machine: 19 passed, 0 failed")
