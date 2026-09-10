#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_plan_exporter.py - generate ams-shell/src/Ams.UI/Services/PlanExporter.cs from
tools/PlanExporter.cs.tpl + firmware/code64b/plan_engine.py (the gen-1 plan engine,
embedded verbatim so an export is self-contained on any machine).

Same anchored-generator pattern as tools/make_fw_template_0.9.64b.py: the engine text is
NOT edited by hand inside the C# file - it is spliced in from the golden firmware line, and
the round trip (extract the literal back out of the generated .cs) must be byte-identical.
Idempotent: regenerating over an up-to-date output is a no-op write of the same bytes.

Usage: python tools/make_plan_exporter.py [repo root]
Exit: 0 = generated + verified, 1 = a guard tripped (nothing half-written).
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / "tools" / "PlanExporter.cs.tpl"
ENGINE = ROOT / "firmware" / "code64b" / "plan_engine.py"
OUT = ROOT / "ams-shell" / "src" / "Ams.UI" / "Services" / "PlanExporter.cs"
MARKER = "__ENGINE_TEMPLATE__"

tpl = TPL.read_text(encoding="utf-8")
engine = ENGINE.read_text(encoding="utf-8")

problems = []
if tpl.count(MARKER) != 1:
    problems.append("template must carry %s exactly once (found %d)" % (MARKER, tpl.count(MARKER)))
if '\ufffd' in tpl or '\ufffd' in engine:
    problems.append("U+FFFD is banned from the source tree")
if '""""' in engine:
    problems.append("the 4-quote delimiter appears inside the engine - bump the delimiter width")
if not engine.startswith("# plan_engine.py"):
    problems.append("firmware/code64b/plan_engine.py lost its header - wrong file?")
if problems:
    print("ABORTING:")
    for p in problems:
        print("  " + p)
    sys.exit(1)

# raw-string literal: 4-quote delimiter (the engine holds triple-quoted docstrings), content at
# column 0 with one empty line before the closing delimiter so the text keeps its trailing \n.
lines = engine.rstrip("\n").split("\n")
literal = '""""\n' + "\n".join(lines + [""]) + '\n""""'
out = tpl.replace(MARKER, literal)

# round trip: pull the literal back out of the generated file and byte-compare with the golden
open_line = next(l for l in out.split("\n") if "EngineTemplate =" in l and l.rstrip().endswith('""""'))
start = out.index(open_line) + len(open_line) + 1
end = out.index('\n"""";')
embedded = out[start:end]
if embedded != engine:
    print("FAIL: round trip mismatch - the embedded engine is not byte-identical to the golden")
    sys.exit(1)

OUT.write_text(out, encoding="utf-8", newline="\n")
print("wrote", OUT.relative_to(ROOT), "(%d chars)" % len(out))
print("engine sha256:", hashlib.sha256(engine.encode("utf-8")).hexdigest())
print("round trip: byte-identical to firmware/code64b/plan_engine.py")
print("MAKE OK")
