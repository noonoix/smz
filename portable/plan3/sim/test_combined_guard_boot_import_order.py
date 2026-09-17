#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")
tree = ast.parse(entry_text)

# Boot must install a small sys.modules proxy before importing the combined
# runtime. The 57 KB executor is loaded only on first symbol access.
module_level_plan_imports = []
for node in tree.body:
    if isinstance(node, ast.Import):
        module_level_plan_imports.extend(alias.name for alias in node.names if alias.name == "plan_engine")
    elif isinstance(node, ast.ImportFrom) and node.module == "plan_engine":
        module_level_plan_imports.append(node.module)
assert not module_level_plan_imports
assert 'class _DeferredPlanEngine:' in entry_text
assert 'sys.modules["plan_engine"] = _DeferredPlanEngine()' in entry_text
assert 'self.module = __import__("plan_engine")' in entry_text
assert entry_text.index('sys.modules["plan_engine"] = _DeferredPlanEngine()') < entry_text.index('import combined_guard_runtime as runtime')
assert "import plan_engine" in runtime_text

# Bundle JSON must be loaded exactly once, before allocating hardware objects.
init_start = entry_text.index("def _memory_safe_init(self):")
init_end = entry_text.index("runtime.Combined.__init__ = _memory_safe_init")
init_text = entry_text[init_start:init_end]
assert init_text.count('runtime.load_guard_bundle("/")') == 1
assert "LightStateGuard.from_bundle" not in init_text
assert init_text.index('runtime.load_guard_bundle("/")') < init_text.index("runtime.Arm()")
assert init_text.index('runtime.load_guard_bundle("/")') < init_text.index("runtime.Keyboard(")
assert init_text.index('runtime.load_guard_bundle("/")') < init_text.index("runtime.BH1750()")
assert "guard.bundle = bundle" in init_text
assert "runtime.Combined.__init__ = _memory_safe_init" in entry_text
assert "runtime.main()" in entry_text
print("combined Guard low-memory boot contract: deferred executor and bundle-first single parse")
