#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_check.py - validate a plan.txt against the REAL plan engine (dogfood).

Usage:  python3 tools/plan_check.py CIRCUITPY/plan.txt [more.txt ...]
Exit:   0 = every file parsed by the engine, 1 = at least one failed.
The parser IS the board's parser (CIRCUITPY/plan_engine.py), so "plan ok" here
means the Pico will accept the file too. '# FLAG' lines are surfaced as warnings.
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.dirname(_HERE), os.path.join(os.path.dirname(_HERE), "CIRCUITPY"),
              os.path.join(_HERE, "CIRCUITPY"), os.getcwd()):
    if os.path.exists(os.path.join(_cand, "plan_engine.py")):
        sys.path.insert(0, _cand)
        break

import plan_engine as pe                                        # noqa: E402


def check(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception as exc:
        print("error: cannot read %s: %s" % (path, exc))
        return False
    flags = [l for l in text.splitlines() if l.startswith("# FLAG")]
    try:
        ops = pe.parse_plan(text)
    except Exception as exc:
        print("FAIL %s: %s" % (path, exc))
        return False
    top = sum(1 for op, _p in ops if not _p.get("_chain"))
    print("plan ok: header %s, %d ops (%d top level)  <- %s" % (
        text.splitlines()[0] if text else "?", len(ops), top, path))
    counts = {}
    for op, _p in ops:
        counts[op] = counts.get(op, 0) + 1
    for op in sorted(counts):
        print("  %-8s %d" % (op, counts[op]))
    for f in flags:
        print("  warning " + f)
    return True


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    ok = True
    for path in argv[1:]:
        ok = check(path) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
