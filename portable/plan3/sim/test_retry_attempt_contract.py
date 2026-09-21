#!/usr/bin/env python3
"""Portable contract for retryAttempt review-pause semantics."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for candidate in (os.path.join(HERE, "CIRCUITPY"), HERE):
    if os.path.exists(os.path.join(candidate, "plan_engine.py")):
        sys.path.insert(0, candidate)
        break
import plan_engine as pe  # noqa: E402

ROUTE = """PLAN|2
RETRY|2,100,50,5,0,esc,alarmAndPauseForReview
KEY|combo=30|hold=0,0
ENDRETRY
"""

class Ctx:
    plan_api = 3
    screen_w = 1920
    screen_h = 1080
    speed_min = 300
    speed_max = 2000

    def __init__(self, results):
        self.results = iter(results)
        self.events = []
        self.alarm = []
        self.review_count = 0

    def log(self, text):
        self.events.append(("log", text))

    def sleep_ms(self, ms):
        self.events.append(("delay", ms))
        return True

    def key_combo(self, vks, hmin, hmax):
        self.events.append(("key", tuple(vks), hmin, hmax))

    def retry_wait_state(self, *_args):
        return next(self.results)

    def retry_alarm(self, text):
        self.alarm.append(text)

    def pause_for_review(self):
        self.review_count += 1
        self.events.append(("review", self.review_count))
        return True

# First attempt times out, Esc is sent, second attempt reaches Desktop light.
c = Ctx([False, True])
pe.run_plan(pe.parse_plan(ROUTE), c)
assert [e[1] for e in c.events if e[0] == "key"] == [(30,), (27,), (30,)]
assert not c.alarm

# Exhaustion alarms and enters review; it resumes only after the light is valid.
c = Ctx([False, False, True])
pe.run_plan(pe.parse_plan(ROUTE), c)
assert c.alarm == ["retryAttempt exhausted"]
assert c.review_count == 1
assert any(e[0] == "review" for e in c.events)

print("retryAttempt portable contract: PASS")
