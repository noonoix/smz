#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cycle_export as ce

assert ce.cycle_lines() == ["RUNFOR|6600,7800", "AUTORESUME|1,180,300"]
assert ce.cycle_lines(root=False) == []

custom = {
    "RestartMinMinutes": 130,
    "RestartMaxMinutes": 110,
    "AutoResumeEnabled": False,
    "AutoResumeMinMinutes": 5,
    "AutoResumeMaxMinutes": 3,
    "BuzzerPin": "GP6",
}
p = ce.CycleExportPolicy(custom)
assert p.root_plan_lines() == ["RUNFOR|6600,7800", "AUTORESUME|0,180,300"]
assert p.include_plan_lines() == []
assert p.as_report() == {
    "restartSeconds": [6600, 7800],
    "autoResumeEnabled": False,
    "resumeSeconds": [180, 300],
    "buzzerPin": "GP6",
}

for bad in ({"RestartMinMinutes": 0}, {"AutoResumeMaxMinutes": -1}, {"BuzzerPin": "GP5"}):
    try:
        ce.CycleExportPolicy(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid cycle settings accepted: %r" % bad)

print("cycle export contract: 10 passed, 0 failed")
