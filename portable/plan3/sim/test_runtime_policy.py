#!/usr/bin/env python3
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import runtime_policy as rp

class Clock:
    def __init__(self, value=1000.0): self.value = value
    def now(self): return self.value

# Defaults and one-time draws.
o = rp.RuntimeOptions()
assert o.as_settings() == {
    "RestartMinMinutes": 110, "RestartMaxMinutes": 130,
    "AutoResumeMinMinutes": 3, "AutoResumeMaxMinutes": 5,
    "AutoResumeEnabled": True, "BuzzerPin": "GP5"}
c = Clock(); cycle = rp.AutoCycle(c.now, o, random.Random(7))
assert 6600 <= cycle.runtime_seconds <= 7800
first_runtime = cycle.runtime_seconds
for _ in range(20): c.value += 10; assert cycle.runtime_seconds == first_runtime
assert not cycle.expired(c.now)
c.value = cycle.deadline; assert cycle.expired(c.now)
first_resume = cycle.arm_resume()
assert 180 <= first_resume <= 300 and cycle.arm_resume() == first_resume

# Custom, swapped, disabled and persistence-compatible settings.
custom = rp.RuntimeOptions(75, 95, 6, 4, True, "gp6")
assert (custom.restart_min_seconds, custom.restart_max_seconds) == (4500, 5700)
assert (custom.resume_min_seconds, custom.resume_max_seconds) == (240, 360)
assert custom.buzzer_pin == "GP6"
round_trip = rp.RuntimeOptions.from_settings(custom.as_settings())
assert round_trip.as_settings() == custom.as_settings()
off = rp.RuntimeOptions(auto_resume=False)
assert rp.AutoCycle(c.now, off, random.Random(1)).arm_resume() is None
for args in ((0, 5, 3, 5), (110, 130, 0, 5)):
    try: rp.RuntimeOptions(*args)
    except ValueError: pass
    else: raise AssertionError("invalid custom range accepted")

# Restart key order and fully ranged holds/gaps.
lines = rp.restart_plan_lines()
downs = [int(x.split("|")[1]) for x in lines if x.startswith("KDOWN|")]
ups = [int(x.split("|")[1]) for x in lines if x.startswith("KUP|")]
assert downs == [91, 88, 38, 38, 13, 38, 13] and ups == downs
for i, line in enumerate(lines):
    if line.startswith("KDOWN|"):
        vk = line.split("|")[1]
        assert lines[i + 1].startswith("DELAY|") and lines[i + 2] == "KUP|" + vk
assert all("," in x for x in lines if x.startswith("DELAY|"))

# GP5/GP6 BEEP only.
assert rp.portable_audio_line("deviceBuzzer", 880, 120, "GP5") == "BEEP|880,120"
assert rp.portable_audio_line("deviceBuzzer", 440, 80, "GP6") == "BEEP|440,80"
for bad_mode in ("playerMacro", "pcSpeaker", "wav", "mp3"):
    try: rp.portable_audio_line(bad_mode)
    except ValueError: pass
    else: raise AssertionError("PC audio accepted")
try: rp.portable_audio_line("deviceBuzzer", buzzer_pin="GP4")
except ValueError: pass
else: raise AssertionError("invalid buzzer pin accepted")

print("runtime policy: 26 passed, 0 failed")
