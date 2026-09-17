#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")
tree = ast.parse(entry_text)

# CircuitPython lacks os.path. Install join/isfile before live_light_guard.
compat_pos = entry_text.index('if not hasattr(_real_os, "path"):')
loader_import_pos = entry_text.index('import live_light_guard as _guard_bundle')
assert compat_pos < loader_import_pos
assert "class _PathCompat:" in entry_text
assert "def join(root, name):" in entry_text
assert "def isfile(path):" in entry_text
assert 'sys.modules["os"] = _OsCompat()' in entry_text
assert '_real_os.stat(path)' in entry_text

# The complete Classroom Studio bundle has 21 files: SHA256SUMS plus 20
# hashed payloads, including its README and metadata JSON.
assert '("pico-calibration.json", "README-FLASH.md")' in entry_text
assert '_guard_bundle.HASHED_BUNDLE_FILES += (_name,)' in entry_text
extras_pos = entry_text.index('for _name in ("pico-calibration.json", "README-FLASH.md"):')
load_pos = entry_text.index('_BOOT_BUNDLE = _guard_bundle.load_guard_bundle("/")')
assert loader_import_pos < extras_pos < load_pos
assert entry_text.count('.load_guard_bundle("/")') == 1

# The large executor stays deferred behind a sys.modules proxy.
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
assert "import plan_engine" in runtime_text

# Parse and verify before importing the large combined runtime.
runtime_pos = entry_text.index('import combined_guard_runtime as runtime')
assert load_pos < runtime_pos
assert 'gc.collect()' in entry_text[load_pos:runtime_pos]
init_start = entry_text.index("def _memory_safe_init(self):")
init_end = entry_text.index("runtime.Combined.__init__ = _memory_safe_init")
init_text = entry_text[init_start:init_end]
assert "load_guard_bundle" not in init_text
assert "bundle = _BOOT_BUNDLE" in init_text
assert "_BOOT_BUNDLE = None" in init_text
assert "LightStateGuard.from_bundle" not in init_text
assert "self.guard.bundle = bundle" in init_text
assert init_text.index("self.bundle = bundle") < init_text.index("runtime.Arm()")
assert "from combined_guard_runtime import main" in entry_text
assert "main()" in entry_text
print("combined Guard boot contract: 20-file manifest, path compatibility, pre-parse and deferred executor")
