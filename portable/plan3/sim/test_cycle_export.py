#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cycle_export as ce

assert ce.cycle_lines() == [
    "RUNFOR|6600,7800", "AUTORESUME|1,180,300", "POSTLAUNCH|1,1,1,3,20,40"]
assert ce.cycle_lines(root=False) == []

custom = {
    "RestartMinMinutes": 130,
    "RestartMaxMinutes": 110,
    "AutoResumeEnabled": False,
    "AutoResumeMinMinutes": 5,
    "AutoResumeMaxMinutes": 3,
    "BuzzerPin": "GP6",
    "PostRestartLaunchEnabled": False,
    "PostRestartTaskbarSlot": 2,
    "PostRestartLaunchBeforeMinSeconds": 2,
    "PostRestartLaunchBeforeMaxSeconds": 4,
    "PostRestartLaunchAfterMinSeconds": 15,
    "PostRestartLaunchAfterMaxSeconds": 30,
}
p = ce.CycleExportPolicy(custom)
assert p.root_plan_lines() == [
    "RUNFOR|6600,7800", "AUTORESUME|0,180,300", "POSTLAUNCH|0,2,2,4,15,30"]
assert p.include_plan_lines() == []
assert p.as_report() == {
    "restartSeconds": [6600, 7800],
    "autoResumeEnabled": False,
    "resumeSeconds": [180, 300],
    "postRestartLaunchEnabled": False,
    "postRestartTaskbarSlot": 2,
    "postRestartLaunchBeforeSeconds": [2, 4],
    "postRestartLaunchAfterSeconds": [15, 30],
    "buzzerPin": "GP6",
}

for bad in ({"RestartMinMinutes": 0}, {"AutoResumeMaxMinutes": -1}, {"BuzzerPin": "GP5"}):
    try:
        ce.CycleExportPolicy(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid cycle settings accepted: %r" % bad)

print("cycle export contract: 15 passed, 0 failed")
