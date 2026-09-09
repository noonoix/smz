#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_plan_diag.py - inject plan-engine DIAGNOSTICS into a Pico code.py.

Why: on the full portable firmware the plan does not move the mouse, and every
failure mode is currently silent or ambiguous:
  * plan_engine.py import failure is swallowed by `except Exception: _pe = None`
  * the engine rejects v2/v3 ops when ctx has no `plan_api` (0.9.65 symptom)
  * plan_pass() may never be reached at all (engine off / paused / host not quiet
    / loop_due() False) and the console shows nothing

This patch ONLY adds prints. It changes no control flow and no protocol string.
It is anchored (fails loudly when an anchor is missing) and idempotent (running
it twice reports 'already present' and rewrites nothing).

Usage:
    python patch_plan_diag.py "E:/code.py"
    python patch_plan_diag.py            # defaults to ./code.py

A backup is written next to the file as <name>.bak-diag (once).
Remove the diagnostics by restoring that backup.
"""
import os
import re
import sys

MARK = "DIAG-PLAN"

DIAG_BLOCK = '''
# ---- DIAG-PLAN (tools/patch_plan_diag.py) - prints only, no behaviour change ----
_diag_pass_n = 0
_diag_mmove_n = 0
_diag_last_gate = 0.0
_diag_booted = False


def _diag(msg):
    print("DIAG " + str(msg))


def _diag_boot_once():
    global _diag_booted
    if _diag_booted:
        return
    _diag_booted = True
    try:
        import os as _os
        _sz = _os.stat(PLAN_PATH)[6]
    except Exception as _e:
        _sz = "MISSING (" + repr(_e) + ")"
    _diag("engine=%s import_error=%s" % ("ok" if _pe is not None else "None", _pe_err))
    _diag("plan file %s size=%s" % (PLAN_PATH, _sz))
    _diag("ctx plan_api=%s" % (getattr(_PlanCtx, "plan_api", "MISSING"),))
    if _pe is not None:
        try:
            _diag("engine ops=%s" % (str(getattr(_pe, "_OPS", "?"))[:110],))
        except Exception:
            pass


def _diag_gate(on, paused, quiet, due):
    global _diag_last_gate
    _t = time.monotonic()
    if _t - _diag_last_gate < 2.0:
        return
    _diag_last_gate = _t
    _diag("gate engine_on=%s paused=%s host_quiet=%s loop_due=%s" % (on, paused, quiet, due))
# ---- end DIAG-PLAN ----
'''

EDITS = [
    (
        "import guard keeps the exception",
        "try:\n    import plan_engine as _pe\nexcept Exception:\n    _pe = None\n",
        "try:\n    import plan_engine as _pe\n    _pe_err = None                      # " + MARK + "\nexcept Exception as _pe_exc:            # " + MARK + "\n    _pe = None\n    _pe_err = repr(_pe_exc)             # " + MARK + "\n" + DIAG_BLOCK,
    ),
    (
        "plan_pass entry trace",
        "    global _plan_cache\n",
        "    global _plan_cache\n"
        "    global _diag_pass_n                 # " + MARK + "\n"
        "    _diag_boot_once()                   # " + MARK + "\n"
        "    _diag_pass_n += 1                   # " + MARK + "\n"
        "    _diag(\"plan_pass #%d engine=%s cache=%s\" % (_diag_pass_n, \"ok\" if _pe is not None else \"None\", \"loaded\" if _plan_cache else str(_plan_cache)))\n",
    ),
    (
        "run error traceback",
        '        print("plan: run error:", exc)\n',
        '        print("plan: run error:", exc)\n'
        "        try:                            # " + MARK + "\n"
        "            import sys as _sys\n"
        "            _sys.print_exception(exc)\n"
        "        except Exception:\n"
        "            pass\n",
    ),
    (
        "main-loop gate trace",
        "            if engine_on and not engine_paused and host_quiet and loop_due():\n",
        "            _diag_boot_once()               # " + MARK + "\n"
        "            _due = loop_due() if (engine_on and not engine_paused and host_quiet) else None\n"
        "            _diag_gate(engine_on, engine_paused, host_quiet, _due)\n"
        "            if _due:\n",
    ),
]

MMOVE_RE = re.compile(r"^([ \t]+)def mmove\(self,\s*x,\s*y\):[ \t]*\n", re.M)


def apply_mmove(src):
    """Log the first MMOVEs the plan asks for (proves the engine reached motion)."""
    m = MMOVE_RE.search(src)
    if not m:
        return src, "MISSING"
    head = m.group(0)
    indent = m.group(1) + "    "
    body = (
        indent + "global _diag_mmove_n            # " + MARK + "\n"
        + indent + "_diag_mmove_n += 1\n"
        + indent + "if _diag_mmove_n <= 5 or _diag_mmove_n % 200 == 0:\n"
        + indent + "    _diag(\"mmove #%d -> %s,%s\" % (_diag_mmove_n, x, y))\n"
    )
    if src[m.end():m.end() + len(body)] == body:
        return src, "already present"
    return src[:m.end()] + body + src[m.end():], "applied"


def main(argv):
    path = argv[1] if len(argv) > 1 else "code.py"
    if not os.path.isfile(path):
        print("error: no such file: %s" % path)
        return 2
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    original = src

    applied = already = missing = 0
    for name, old, new in EDITS:
        if new in src:
            print("already present: %s" % name)
            already += 1
            continue
        count = src.count(old)
        if count != 1:
            print("MISSING ANCHOR (%d matches): %s" % (count, name))
            missing += 1
            continue
        src = src.replace(old, new, 1)
        print("applied: %s" % name)
        applied += 1

    src, mstate = apply_mmove(src)
    print("%s: mmove trace" % mstate)
    if mstate == "applied":
        applied += 1
    elif mstate == "MISSING":
        missing += 1
    else:
        already += 1

    if missing:
        print("\nFAIL: %d anchor(s) not found - nothing written." % missing)
        print("Send the first 30 lines of your code.py so the anchors can be re-cut.")
        return 1

    if src == original:
        print("\nPASS: already patched (%d edits present) - file untouched." % already)
        return 0

    backup = path + ".bak-diag"
    if not os.path.exists(backup):
        with open(backup, "w", encoding="utf-8") as fh:
            fh.write(original)
        print("backup: %s" % backup)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    print("\nPASS: %d applied, %d already present -> %s" % (applied, already, path))
    print("Boot the Pico and watch the console: DIAG lines report engine import,")
    print("plan file size, ctx plan_api, the run gate every 2 s and the first MMOVEs.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
