#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime.read_text(encoding="utf-8")
ast.parse(entry_text)

# CircuitPython must load the 57 KB executor on a freshly collected heap before
# combined_guard_runtime defines hardware classes and imports the same module.
gc_pos = entry_text.index("gc.collect()")
engine_pos = entry_text.index("import plan_engine")
combined_pos = entry_text.index("from combined_guard_runtime import main")
assert gc_pos < engine_pos < combined_pos
assert entry_text.count("gc.collect()") >= 2
assert "import plan_engine" in runtime_text
assert "main()" in entry_text
print("combined Guard boot import-order contract: plan_engine loads first on a compact heap")
