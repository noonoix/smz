#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime.read_text(encoding="utf-8")
tree = ast.parse(entry_text)

# Boot must install a small sys.modules proxy before combined_guard_runtime's
# top-level import. The 57 KB executor is loaded only on first symbol access.
module_level_plan_imports = []
for node in tree.body:
    if isinstance(node, ast.Import):
        module_level_plan_imports.extend(alias.name for alias in node.names if alias.name == "plan_engine")
    elif isinstance(node, ast.ImportFrom) and node.module == "plan_engine":
        module_level_plan_imports.append(node.module)
assert not module_level_plan_imports
assert 'class _DeferredPlanEngine:' in entry_text
assert 'sys.modules["plan_engine"] = _DeferredPlanEngine()' in entry_text
assert 'del sys.modules["plan_engine"]' in entry_text
assert 'gc.collect()' in entry_text
assert 'self.module = __import__("plan_engine")' in entry_text
assert entry_text.index('sys.modules["plan_engine"] = _DeferredPlanEngine()') < entry_text.index('from combined_guard_runtime import main')
assert "import plan_engine" in runtime_text
assert "main()" in entry_text
print("combined Guard boot import-order contract: plan_engine deferred until route execution")
