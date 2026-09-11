#!/usr/bin/env python3
"""Apply the PLAN2 h5 hardware-acceptance fixes.

Fixes:
1. Share the core PlanAbort type with the lazily imported motion module.
2. Normalize standalone run state and Num Lock after the final configured pass.
3. Add a regression that aborts from inside the lazy motion module.

Idempotent and forward-aware: a repository already upgraded to h6 satisfies the
superseded h5 completion requirement. Generated split/runtime files are rebuilt
by the normal PLAN2 workflow.
"""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SPLITTER = ROOT / "tools" / "split_plan_engine.py"
FIRMWARE = ROOT / "ams-shell" / "src" / "Ams.UI" / "Services" / "PicoFirmwareExporter.cs"
SPLIT_TEST = ROOT / "portable" / "plan3" / "sim" / "test_split_engine.py"
MARKER = "PLAN2_H5_CONTROL_FIX"
H6_MARKER = "PLAN2_H6_CONTROL_FIX"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: anchor count {count}, expected 1")
    return text.replace(old, new, 1)


# The lazy module has its own globals. Bind the canonical abort class explicitly so
# an interrupted before/path/after delay raises plan_engine.PlanAbort, not NameError.
s = SPLITTER.read_text(encoding="utf-8")
if MARKER not in s:
    s = replace_once(
        s,
        "    if _motion_module is None:\\n        import plan_motion as _motion_module\\n    return _motion_module._exec_rmouse(prm, ctx, pauses, pos, target)",
        "    if _motion_module is None:\\n        import plan_motion as _motion_module\\n        _motion_module.PlanAbort = PlanAbort  # PLAN2_H5_CONTROL_FIX: one shared abort type\\n    return _motion_module._exec_rmouse(prm, ctx, pauses, pos, target)",
        "lazy motion abort binding",
    )
    SPLITTER.write_text(s, encoding="utf-8", newline="\n")
    print("h5: split abort binding applied")
else:
    print("h5: split abort binding already applied")


# A completed once/times/timed macro must become stopped immediately. h6 supersedes
# this implementation with finite-plan-aware completion, so treat h6 as satisfied.
f = FIRMWARE.read_text(encoding="utf-8")
if H6_MARKER in f:
    print("h5: natural completion superseded by h6")
elif MARKER not in f:
    old = '''                    if engine_on and not engine_paused and host_quiet and loop_due():
                        if plan_pass():            # v0.9.61 - a portable plan takes precedence
                            passes += 1
                        elif states:
                            standalone_pass()
                            passes += 1
                    time.sleep(0.02)'''
    new = '''                    if engine_on and not engine_paused and host_quiet and loop_due():
                        _completed_pass = False
                        if plan_pass():            # v0.9.61 - a portable plan takes precedence
                            passes += 1
                            _completed_pass = True
                        elif states:
                            standalone_pass()
                            passes += 1
                            _completed_pass = True
                        if _completed_pass and not loop_due():
                            # PLAN2_H5_CONTROL_FIX: natural once/times/timed completion is a
                            # real Stop. Turn the engine and pause state off and mirror it via
                            # Num Lock, so the next GP4 edge starts with one press.
                            engine_on = False
                            engine_paused = False
                            release_all_buttons()
                            tap_key(Keycode.KEYPAD_NUMLOCK)
                    time.sleep(0.02)'''
    f = replace_once(f, old, new, "natural completion state")
    FIRMWARE.write_text(f, encoding="utf-8", newline="\n")
    print("h5: natural completion normalization applied")
else:
    print("h5: natural completion normalization already applied")


t = SPLIT_TEST.read_text(encoding="utf-8")
if MARKER not in t:
    test = '''# PLAN2_H5_CONTROL_FIX: aborting inside lazy motion must use the core exception.
class AbortMotionCtx(Ctx):
    def sleep_ms(self, m):
        self.ev.append(("delay", m))
        return False

abort_text = "PLAN|2\\nSCREEN|1920,1080\\nRMOUSE|region=100,120,200,150|before=1,1|after=0,0|curve=15,45|mid=0:0,0|over=0|idle=1,1:0,0"
for engine, name in ((canonical, "canonical"), (split, "split")):
    caught = False
    try:
        engine.run_plan(engine.parse_plan(abort_text), AbortMotionCtx())
    except engine.PlanAbort:
        caught = True
    assert caught, name + " did not raise its exported PlanAbort"
print("PASS h5 lazy-motion PlanAbort parity"); passed += 1

'''
    t = replace_once(t, "bundle = {\n", test + "bundle = {\n", "split abort regression")
    SPLIT_TEST.write_text(t, encoding="utf-8", newline="\n")
    print("h5: split abort regression applied")
else:
    print("h5: split abort regression already applied")

# Postconditions catch partial application immediately while accepting the h6
# implementation that intentionally replaces h5's legacy loop-mode condition.
assert "_motion_module.PlanAbort = PlanAbort" in SPLITTER.read_text(encoding="utf-8")
fw = FIRMWARE.read_text(encoding="utf-8")
h5_completion = "_completed_pass and not loop_due()" in fw
h6_completion = H6_MARKER in fw and '_plan_result == "done"' in fw
assert (h5_completion or h6_completion) and "tap_key(Keycode.KEYPAD_NUMLOCK)" in fw
assert "PASS h5 lazy-motion PlanAbort parity" in SPLIT_TEST.read_text(encoding="utf-8")
print("PLAN2 h5 hotfix OK")
