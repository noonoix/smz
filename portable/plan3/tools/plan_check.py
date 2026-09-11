#!/usr/bin/env python3
"""Blocking validator for portable plans (plan.txt).

Parses the plan with the REAL engine, so anything the Pico would reject fails here
first. It also surfaces every '# FLAG' line, because a plan is only "fully covered"
when nothing was skipped silently.

Usage: python3 plan_check.py plan.txt
Exit 0 = safe to copy to the board, 1 = do not ship.
"""
import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _cand in (_ROOT, os.path.join(_ROOT, "CIRCUITPY"), _HERE, os.getcwd()):
    if os.path.exists(os.path.join(_cand, "plan_engine.py")):
        sys.path.insert(0, _cand)
        break
import plan_engine as pe                                        # noqa: E402


def walk(ops, depth=0):
    for op, prm in ops:
        yield op, depth
        if isinstance(prm, dict):
            for sub in prm.get("progs", ()):
                for item in walk(sub, depth + 1):
                    yield item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    text = open(args.plan, "r").read()
    try:
        ops = pe.parse_plan(text)
    except Exception as exc:
        print("INVALID PLAN: %s" % exc)
        return 1
    if not ops or ops[0][0] != "PLAN":
        print("INVALID PLAN: missing PLAN|2 header")
        return 1
    counts = {}
    total = 0
    for op, _depth in walk(ops):
        counts[op] = counts.get(op, 0) + 1
        total += 1
    print("plan ok: header PLAN|%s, %d ops (%d top level)"
          % (ops[0][1].get("v"), total, len(ops)))
    if not args.quiet:
        for key in sorted(counts):
            print("  %-9s %d" % (key, counts[key]))
    flags = [ln.strip() for ln in text.split("\n") if ln.strip().startswith("# FLAG")]
    if flags:
        print("flags that need a PC or a manual decision:")
        for flag in flags:
            print("  " + flag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
