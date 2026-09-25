#!/usr/bin/env python3
"""Per-TYPE human typo count contract.

The persisted Studio keys remain typoEveryMin/Max for .amsj compatibility, but
new portable plans use typos=min,max. Legacy typo=min,max cadence stays readable.
"""
from pathlib import Path
import importlib.util
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
MODERN = ROOT / "CIRCUITPY-MODERN"
SPLIT = ROOT / "CIRCUITPY-SPLIT"
REPO = ROOT.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(MODERN))
for module_name in ("plan_engine_parse", "plan_engine_human"):
    sys.modules.pop(module_name, None)
parse = __import__("plan_engine_parse")
human = __import__("plan_engine_human")
split_typing = load("typo_count_split", SPLIT / "plan_typing.py")


def replay(commands):
    text = ""
    backspaces = 0
    for command in commands:
        if command[0] == "KTEXT":
            text += command[3]
        elif command[0] == "KCOMBO" and command[1] == 8:
            text = text[:-1]
            backspaces += 1
    return text, backspaces


plan = parse.parse_plan(
    "PLAN|2\nTYPE|text=zodiak999999|h=111,250|typos=3,5"
)
params = plan[1][1]
assert params["typos"] == (3, 5)

for planner in (human.plan_typing, split_typing.plan_typing):
    observed = set()
    for seed in range(40):
        random.seed(seed)
        final_text, count = replay(planner(params["text"], params))
        assert final_text == "zodiak999999"
        assert 3 <= count <= 5
        observed.add(count)
    assert observed == {3, 4, 5}, observed

    # Count mode applies to characters, including a one-character text.
    random.seed(7)
    final_text, count = replay(planner("a", {"h": (1, 1), "typos": (1, 1)}))
    assert final_text == "a" and count == 1

    # An impossible requested count is safely capped at eligible characters.
    random.seed(9)
    final_text, count = replay(planner("a!", {"h": (1, 1), "typos": (4, 8)}))
    assert final_text == "a!" and count == 1

    # The old every-N-words wire contract remains readable for old plan files.
    random.seed(11)
    final_text, count = replay(planner("one two", {"h": (1, 1), "typo": (1, 1)}))
    assert final_text == "one two" and count == 2


route = (MODERN / "login_or_dc_steps.txt").read_text(encoding="utf-8")
assert "|typos=3,5" in route and "|typo=3,5" not in route

exporter = (REPO / "ams-shell/src/Ams.UI/Services/PlanExporter.cs").read_text(encoding="utf-8")
assert 'parts.Add("typos=" + y0 + "," + y1)' in exporter
assert "for k in ('h', 'w', 'p', 'typo', 'typos')" in exporter
assert "typo_count_mode = typo_count_max > 0" in exporter

labels = (REPO / "ams-shell/src/Ams.UI/Models/StepTextsFa.cs").read_text(encoding="utf-8")
assert "تعداد خطای تایپی در همین متن" in labels

generator = (ROOT / "tools/plan_gen.py").read_text(encoding="utf-8")
assert 'parts.append("typos=%d,%d"' in generator

print("per-TYPE typo count contract: PASS")