#!/usr/bin/env python3
import json
import sys
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "tools"))
sys.path.insert(0, str(base / "CIRCUITPY"))
import plan_gen
import plan_gen_autocycle as auto
import plan_cycle

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    child = td / "child.amsj"
    child.write_text(json.dumps({"app": "AMS", "steps": [
        {"Type": "delay", "Delay": 0, "Props": {"minMs": 1, "maxMs": 2}, "Children": []}
    ]}), encoding="utf-8")
    root = td / "root.amsj"
    root.write_text(json.dumps({"app": "AMS", "steps": [
        {"Type": "playScript", "Delay": 0, "Props": {"path": str(child)}, "Children": []}
    ]}), encoding="utf-8")
    settings = plan_gen.load_settings(None)
    settings.update({
        "RestartMinMinutes": 110, "RestartMaxMinutes": 130,
        "AutoResumeEnabled": True,
        "AutoResumeMinMinutes": 3, "AutoResumeMaxMinutes": 5,
        "PostRestartLaunchEnabled": True,
        "PostRestartTaskbarSlot": 1,
        "PostRestartLaunchBeforeMinSeconds": 1,
        "PostRestartLaunchBeforeMaxSeconds": 3,
        "PostRestartLaunchAfterMinSeconds": 20,
        "PostRestartLaunchAfterMaxSeconds": 40,
        "BuzzerPin": "GP6",
    })
    opts = {"screen_w": 1920, "screen_h": 1080, "settings": settings,
            "type_key_min": 80, "type_key_max": 220, "out_name": "plan.txt"}
    files, _gen, _children = auto.build(str(root), opts)
    assert files["plan.txt"].splitlines()[1:4] == [
        "RUNFOR|6600,7800", "AUTORESUME|1,180,300", "POSTLAUNCH|1,1,1,3,20,40"]
    assert "RUNFOR|" not in files["child.txt"]
    assert "AUTORESUME|" not in files["child.txt"]
    assert "POSTLAUNCH|" not in files["child.txt"]
    ops, policy = plan_cycle.parse_cycle_plan(files["plan.txt"])
    assert policy == {
        "run": (6600, 7800), "auto": True, "resume": (180, 300),
        "launch": (True, 1, (1, 3), (20, 40)),
    }
    assert any(op == "INCLUDE" for op, _ in ops)

plain = "PLAN|2\nDELAY|1\n"
custom = {
    "RestartMinMinutes": 20, "RestartMaxMinutes": 10,
    "AutoResumeEnabled": False,
    "AutoResumeMinMinutes": 8, "AutoResumeMaxMinutes": 6,
    "PostRestartLaunchEnabled": False,
    "PostRestartTaskbarSlot": 3,
    "PostRestartLaunchBeforeMinSeconds": 4,
    "PostRestartLaunchBeforeMaxSeconds": 2,
    "PostRestartLaunchAfterMinSeconds": 9,
    "PostRestartLaunchAfterMaxSeconds": 7,
    "BuzzerPin": "GP6",
}
text = auto.inject_root_policy(plain, custom)
assert text.splitlines()[1:4] == [
    "RUNFOR|600,1200", "AUTORESUME|0,360,480", "POSTLAUNCH|0,3,2,4,7,9"]
print("plan_gen auto-cycle: 17 passed, 0 failed")
