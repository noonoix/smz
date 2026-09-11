#!/usr/bin/env python3
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import runtime_policy as rp

class Clock:
    def __init__(self, value=1000.0): self.value = value
    def now(self): return self.value

o = rp.RuntimeOptions()
assert o.as_settings() == {
    "RestartMinMinutes": 110, "RestartMaxMinutes": 130,
    "AutoResumeMinMinutes": 3, "AutoResumeMaxMinutes": 5,
    "AutoResumeEnabled": True, "BuzzerPin": "GP6"}
c = Clock(); cycle = rp.AutoCycle(c.now, o, random.Random(7))
assert 6600 <= cycle.runtime_seconds <= 7800
first_runtime = cycle.runtime_seconds
for _ in range(20): c.value += 10; assert cycle.runtime_seconds == first_runtime
assert not cycle.expired(c.now)
c.value = cycle.deadline; assert cycle.expired(c.now)
first_resume = cycle.arm_resume()
assert 180 <= first_resume <= 300 and cycle.arm_resume() == first_resume

custom = rp.RuntimeOptions(75, 95, 6, 4, True, "gp6")
assert (custom.restart_min_seconds, custom.restart_max_seconds) == (4500, 5700)
assert (custom.resume_min_seconds, custom.resume_max_seconds) == (240, 360)
assert custom.buzzer_pin == "GP6"
assert rp.RuntimeOptions.from_settings(custom.as_settings()).as_settings() == custom.as_settings()
off = rp.RuntimeOptions(auto_resume=False)
assert rp.AutoCycle(c.now, off, random.Random(1)).arm_resume() is None
for args in ((0, 5, 3, 5), (110, 130, 0, 5)):
    try: rp.RuntimeOptions(*args)
    except ValueError: pass
    else: raise AssertionError("invalid custom range accepted")

lines = rp.restart_plan_lines()
# Exact Win+X lifecycle: Win stays down until X is released.
combo = ["KDOWN|91", "DELAY|25,60", "KDOWN|88", "DELAY|45,95",
         "KUP|88", "DELAY|25,60", "KUP|91", "DELAY|450,850"]
assert lines[1:9] == combo
assert lines.index("KUP|88") < lines.index("KUP|91")
downs = [int(x.split("|")[1]) for x in lines if x.startswith("KDOWN|")]
ups = [int(x.split("|")[1]) for x in lines if x.startswith("KUP|")]
assert downs == [91, 88, 38, 38, 13, 38, 13]
assert ups == [88, 91, 38, 38, 13, 38, 13]
assert all("," in x for x in lines if x.startswith("DELAY|"))

assert rp.portable_audio_line("deviceBuzzer", 440, 80, "GP6") == "BEEP|440,80"
for bad_mode in ("playerMacro", "pcSpeaker", "wav", "mp3"):
    try: rp.portable_audio_line(bad_mode)
    except ValueError: pass
    else: raise AssertionError("PC audio accepted")
for invalid_pin in ("GP4", "GP5"):
    try: rp.portable_audio_line("deviceBuzzer", buzzer_pin=invalid_pin)
    except ValueError: pass
    else: raise AssertionError("non-GP6 buzzer pin accepted")

print("runtime policy: 30 passed, 0 failed")
