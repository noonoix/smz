from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "portable/plan3/CIRCUITPY/plan_engine.py"
text = ENGINE.read_text(encoding="utf-8")

# The first application accidentally inserted the executor branch into the
# parser because both sections used the same WLIGHT anchor. Remove that bad
# branch, then insert it at the real executor anchor.
bad = '''        elif op == "STATELOOP":
            # v4: the portable live light guard owns routing and returns only
            # when the keypad stops the run or the sensor becomes unsafe.
            _run_state_loop(prm, ctx, pos, pauses, inc)
'''
if bad in text:
    text = text.replace(bad, "", 1)

branch = '''        elif op == "STATELOOP":
            # v4: the portable live light guard owns routing and returns only
            # when the keypad stops the run or the sensor becomes unsafe.
            _run_state_loop(prm, ctx, pos, pauses, inc)
'''

# After removing the parser mistake, the remaining WLIGHT branch is the
# executor branch. Do not add the branch twice on retries.
if branch not in text:
    anchor = '        elif op == "WLIGHT":\n'
    if anchor not in text:
        raise SystemExit("plan_engine: executor WLIGHT anchor not found")
    text = text.replace(anchor, branch + anchor, 1)

ENGINE.write_text(text, encoding="utf-8")
print("corrected STATELOOP placement")
