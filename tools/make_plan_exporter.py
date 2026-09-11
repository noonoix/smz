#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate PlanExporter.cs with the three-file, memory-fit PLAN|2 runtime.

The split files are regenerated from the canonical engine first. Each C# raw
literal is round-tripped and byte-compared with its generated Python source.
"""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / "tools" / "PlanExporter.cs.tpl"
CANONICAL = ROOT / "portable" / "plan3" / "CIRCUITPY" / "plan_engine.py"
SPLIT = ROOT / "portable" / "plan3" / "CIRCUITPY-SPLIT"
OUT = ROOT / "ams-shell" / "src" / "Ams.UI" / "Services" / "PlanExporter.cs"
SPLITTER = ROOT / "tools" / "split_plan_engine.py"
MODULES = (
    ("plan_engine.py", "__ENGINE_CORE_TEMPLATE__", "EngineTemplate ="),
    ("plan_motion.py", "__ENGINE_MOTION_TEMPLATE__", "MotionTemplate ="),
    ("plan_typing.py", "__ENGINE_TYPING_TEMPLATE__", "TypingTemplate ="),
)

subprocess.run([sys.executable, str(SPLITTER), str(CANONICAL), str(SPLIT)], check=True)
tpl = TPL.read_text(encoding="utf-8")
problems = []
for name, marker, _ in MODULES:
    if tpl.count(marker) != 1:
        problems.append(f"template must carry {marker} exactly once (found {tpl.count(marker)})")
    text = (SPLIT / name).read_text(encoding="utf-8")
    if "\ufffd" in text:
        problems.append(f"U+FFFD is banned from {name}")
    if '""""' in text:
        problems.append(f"4-quote delimiter appears inside {name}")
if problems:
    print("ABORTING:")
    for problem in problems:
        print("  " + problem)
    raise SystemExit(1)

out = tpl
expected = {}
for name, marker, _ in MODULES:
    text = (SPLIT / name).read_text(encoding="utf-8")
    expected[name] = text
    literal = '""""\n' + text.rstrip("\n") + '\n\n""""'
    out = out.replace(marker, literal, 1)

for name, _, declaration in MODULES:
    line = next(line for line in out.split("\n") if declaration in line and line.rstrip().endswith('""""'))
    start = out.index(line) + len(line) + 1
    end = out.index('\n"""";', start)
    embedded = out[start:end]
    if embedded != expected[name]:
        print(f"FAIL: {name} embedded round trip mismatch")
        raise SystemExit(1)

OUT.write_text(out, encoding="utf-8", newline="\n")
print("wrote", OUT.relative_to(ROOT), f"({len(out)} chars)")
for name, _, _ in MODULES:
    data = expected[name].encode("utf-8")
    print(name, len(data), hashlib.sha256(data).hexdigest())
print("round trip: all three split modules byte-identical")
print("MAKE OK")
