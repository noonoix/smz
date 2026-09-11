#!/usr/bin/env python3
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import resume_essentials as re

items = [
    re.EssentialItem("food", 55, 57 * 60, 63 * 60, priority=20),
    re.EssentialItem("potion", 54, 28 * 60, 32 * 60, priority=10),
    re.EssentialItem("tea", 53, 270, 330, priority=30),
    re.EssentialItem("disabled", 52, 60, 90, enabled=False),
]
s = re.EssentialScheduler(items, random.Random(42))

pkg = s.resume_package()
assert len(pkg) == 3
assert {x.name for x in pkg} == {"food", "potion", "tea"}
assert len({id(x) for x in pkg}) == 3

lines = re.package_plan_lines(pkg)
for item in pkg:
    marker = lines.index("# essential: " + item.name)
    assert lines[marker + 1].startswith("DELAY|")
    assert lines[marker + 2] == "KDOWN|%d" % item.vk
    assert lines[marker + 3].startswith("DELAY|")
    assert lines[marker + 4] == "KUP|%d" % item.vk
    assert lines[marker + 5].startswith("DELAY|")
assert all("," in x for x in lines if x.startswith("DELAY|"))

s.mark_resume_success(1000, pkg)
for item in pkg:
    lo, hi = item.interval
    assert 1000 + lo <= item.next_due <= 1000 + hi
assert items[3].next_due is None

assert s.due_at_safe_boundary(1001) == []
for item in pkg: item.next_due = 2000
assert [x.name for x in s.due_at_safe_boundary(2000)] == ["potion", "food", "tea"]

tea = items[2]
next_due = s.mark_success(tea, 3000)
assert 3270 <= next_due <= 3330

for bad in (
    lambda: re.EssentialItem("", 55, 1, 2),
    lambda: re.EssentialItem("x", 0, 1, 2),
    lambda: re.EssentialItem("x", 55, 0, 2),
):
    try: bad()
    except ValueError: pass
    else: raise AssertionError("invalid essential accepted")
try:
    re.EssentialScheduler([re.EssentialItem("x", 1, 1, 2), re.EssentialItem("x", 2, 1, 2)])
except ValueError: pass
else: raise AssertionError("duplicate essential name accepted")

print("resume essentials: 24 passed, 0 failed")
