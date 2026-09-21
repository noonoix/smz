#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression contract for the Pico portable randomPackage route.

This is intentionally independent of Classroom Studio execution.  The route is
what is copied to the Pico, and the test exercises the same plan_engine parser
and executor used by the portable firmware.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for candidate in (os.path.join(ROOT, "CIRCUITPY"), ROOT, HERE):
    if os.path.exists(os.path.join(candidate, "plan_engine.py")):
        sys.path.insert(0, candidate)
        break

import plan_engine as pe  # noqa: E402

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name)


class Ctx:
    plan_api = 3
    screen_w = 1920
    screen_h = 1080
    speed_min = 300
    speed_max = 2000

    def __init__(self):
        self.now_s = 0.0
        self.events = []

    def now(self):
        return self.now_s

    def gate(self):
        return True

    def sleep_ms(self, ms):
        self.now_s += int(ms) / 1000.0
        self.events.append(("delay", int(ms)))
        return True

    def key_combo(self, vks, hmin, hmax):
        self.events.append(("key", tuple(vks), hmin, hmax))

    def log(self, text):
        self.events.append(("log", text))

    def setres(self, width, height):
        self.events.append(("screen", width, height))


def keys(ctx):
    return [event[1][0] for event in ctx.events if event[0] == "key"]


def delays(ctx):
    return [event[1] for event in ctx.events if event[0] == "delay"]


def key_delay_pairs(ctx):
    pairs = []
    pending = None
    for event in ctx.events:
        if event[0] == "key":
            pending = event[1][0]
        elif event[0] == "delay" and pending is not None:
            pairs.append((pending, event[1]))
            pending = None
    return pairs


ROUTE = """PLAN|2
SCREEN|1920,1080
SPEED|300,2000
LOOP|2
RPKG|all,1,6
KEY|combo=49
DELAY|88,188
PKGITEM
KEY|combo=50
DELAY|122,222
PKGITEM
KEY|combo=51
DELAY|111,444
PKGITEM
KEY|combo=52
DELAY|44,222
PKGITEM
KEY|combo=53
DELAY|555,888
PKGITEM
KEY|combo=54
DELAY|124,190
ENDPKG
ENDLOOP
"""

# all-random means all six children exactly once per loop pass.
ops = pe.parse_plan(ROUTE)
ctx = Ctx()
random.seed(20260921)
pe.run_plan(ops, ctx)
first = keys(ctx)
check("all-random executes every child once per pass", len(first) == 12
      and sorted(first[:6]) == [49, 50, 51, 52, 53, 54]
      and sorted(first[6:]) == [49, 50, 51, 52, 53, 54])
check("all-random produces a shuffled order", first[:6] != [49, 50, 51, 52, 53, 54])
check("each DelayMax is executed after its child", len(delays(ctx)) == 12)

ranges = {49: (88, 188), 50: (122, 222), 51: (111, 444),
          52: (44, 222), 53: (555, 888), 54: (124, 190)}
for index, (vk, value) in enumerate(key_delay_pairs(ctx)):
    lo, hi = ranges[vk]
    check("random delay stays inside the child's range %d" % index, lo <= value <= hi)

# some-random maps to portable pick mode: inclusive count, no replacement.
PICK = ROUTE.replace("RPKG|all,1,6", "RPKG|pick,2,4")
subsets = set()
for seed in range(12):
    c = Ctx()
    random.seed(seed)
    pe.run_plan(pe.parse_plan(PICK), c)
    selected = keys(c)
    subsets.add(tuple(selected))
    check("some-random count is inclusive and bounded %d" % seed, 2 <= len(selected) <= 4)
    check("some-random has no duplicate child %d" % seed, len(selected) == len(set(selected)))
check("some-random can draw fresh subsets", len(subsets) > 1)

# Nested packages are parsed and executed recursively; child delays stay local.
NESTED = """PLAN|2
RPKG|all,1,2
RPKG|all,1,2
KEY|combo=65
DELAY|10,20
PKGITEM
KEY|combo=66
DELAY|10,20
ENDPKG
PKGITEM
KEY|combo=67
DELAY|30,40
ENDPKG
"""
c = Ctx()
random.seed(7)
pe.run_plan(pe.parse_plan(NESTED), c)
check("nested randomPackage executes recursively", sorted(keys(c)) == [65, 66, 67])
check("nested child delays remain bounded", all(10 <= d <= 40 for d in delays(c)))

fixture = os.path.join(ROOT, "examples", "random-package-delay.plan.txt")
with open(fixture, "r", encoding="utf-8") as fh:
    check("reference hardware route parses", bool(pe.parse_plan(fh.read())))

print("randomPackage portable contract: %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
