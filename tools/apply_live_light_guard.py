from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "portable/plan3/CIRCUITPY/plan_engine.py"
text = ENGINE.read_text(encoding="utf-8")

# Remove any misplaced STATELOOP executor branch left in the parser. The
# parser's own STATELOOP branch is intentionally different and is preserved.
branch = '''        elif op == "STATELOOP":
            # v4: the portable live light guard owns routing and returns only
            # when the keypad stops the run or the sensor becomes unsafe.
            _run_state_loop(prm, ctx, pos, pauses, inc)
'''
while branch in text:
    text = text.replace(branch, "", 1)

# The executor WLIGHT branch has a unique body, unlike the parser's WLIGHT
# parser branch. Insert exactly once at that anchor.
anchor = '''        elif op == "WLIGHT":
            ok = ctx.wait_light(prm["lo"], prm["hi"], prm["stable"], prm["to"], prm["mode"])
'''
if anchor not in text:
    raise SystemExit("plan_engine: executor WLIGHT anchor not found")
if branch not in text:
    text = text.replace(anchor, branch + anchor, 1)

ENGINE.write_text(text, encoding="utf-8")
print("corrected STATELOOP placement")
