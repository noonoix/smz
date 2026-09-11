#!/usr/bin/env python3
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import runtime_policy as rp


class Clock:
    def __init__(self, value=1000.0): self.value = value
    def now(self): return self.value


clock = Clock()
policy = rp.WallClockRuntime(clock.now, random.Random(7))
assert 6600 <= policy.duration_seconds <= 7800
selected = policy.duration_seconds
for _ in range(20):
    clock.value += 10
    assert policy.duration_seconds == selected
assert not policy.expired(clock.now)
clock.value = policy.deadline
assert policy.expired(clock.now)

lo, hi = rp.normalize_runtime_range(7800, 6600)
assert (lo, hi) == (6600, 7800)
try:
    rp.normalize_runtime_range(0, 10)
except ValueError:
    pass
else:
    raise AssertionError("non-positive runtime was accepted")

lines = rp.restart_plan_lines()
downs = [int(x.split("|")[1]) for x in lines if x.startswith("KDOWN|")]
ups = [int(x.split("|")[1]) for x in lines if x.startswith("KUP|")]
assert downs == [91, 88, 38, 38, 13, 38, 13]
assert ups == downs
for i, line in enumerate(lines):
    if line.startswith("KDOWN|"):
        vk = line.split("|")[1]
        assert lines[i + 1].startswith("DELAY|")
        assert lines[i + 2] == "KUP|" + vk
        a, b = map(int, lines[i + 1].split("|")[1].split(","))
        assert 0 < a < b
assert all("," in line for line in lines if line.startswith("DELAY|"))

assert rp.portable_audio_line("deviceBuzzer", 880, 120) == "BEEP|880,120"
for bad in ("playerMacro", "pcSpeaker", "wav", "mp3"):
    try:
        rp.portable_audio_line(bad)
    except ValueError as exc:
        assert "buzzer" in str(exc)
    else:
        raise AssertionError("PC audio mode was accepted: " + bad)
try:
    rp.portable_audio_line("deviceBuzzer", 880, 120, "GP4")
except ValueError as exc:
    assert "GP5" in str(exc)
else:
    raise AssertionError("non-GP5 buzzer pin was accepted")

print("runtime policy: 18 passed, 0 failed")
