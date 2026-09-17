#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")
ast.parse(entry_text)

loader_pos = entry_text.index('import live_light_guard as _guard_bundle')

# CircuitPython lacks os.path on the target build.
assert entry_text.index('if not hasattr(_real_os, "path"):') < loader_pos
assert "class _PathCompat:" in entry_text
assert 'sys.modules["os"] = _OsCompat()' in entry_text
assert '_real_os.stat(path)' in entry_text

# CircuitPython exposes hashlib.new("sha256") but not hashlib.sha256, while
# the shared verifier also needs hexdigest(). Install both before its import.
assert entry_text.index('if not hasattr(_real_hashlib, "sha256"):') < loader_pos
assert "class _Sha256Compat:" in entry_text
assert "class _HashlibCompat:" in entry_text
assert '_real_hashlib.new("sha256")' in entry_text
assert 'def hexdigest(self):' in entry_text
assert 'sys.modules["hashlib"] = _HashlibCompat()' in entry_text
assert 'CircuitPython hashlib has no SHA-256 implementation' in entry_text

# The complete export has SHA256SUMS plus 20 hashed payloads.
assert '("pico-calibration.json", "README-FLASH.md")' in entry_text
assert '_guard_bundle.HASHED_BUNDLE_FILES += (_name,)' in entry_text
extras_pos = entry_text.index('for _name in ("pico-calibration.json", "README-FLASH.md"):')
load_pos = entry_text.index('_BOOT_BUNDLE = _guard_bundle.load_guard_bundle("/")')
assert loader_pos < extras_pos < load_pos
assert entry_text.count('.load_guard_bundle("/")') == 1

# The large executor stays deferred.
assert 'class _DeferredPlanEngine:' in entry_text
assert 'sys.modules["plan_engine"] = _DeferredPlanEngine()' in entry_text
assert 'self.module = __import__("plan_engine")' in entry_text
assert "import plan_engine" in runtime_text

# Verify before importing the combined hardware runtime, then reuse the bundle.
runtime_pos = entry_text.index('import combined_guard_runtime as runtime')
assert load_pos < runtime_pos
assert 'gc.collect()' in entry_text[load_pos:runtime_pos]
init_start = entry_text.index("def _memory_safe_init(self):")
init_end = entry_text.index("runtime.Combined.__init__ = _memory_safe_init")
init_text = entry_text[init_start:init_end]
assert "load_guard_bundle" not in init_text
assert "bundle = _BOOT_BUNDLE" in init_text
assert "_BOOT_BUNDLE = None" in init_text
assert "self.guard.bundle = bundle" in init_text
assert init_text.index("self.bundle = bundle") < init_text.index("runtime.Arm()")
assert "from combined_guard_runtime import main" in entry_text
assert "main()" in entry_text
print("combined Guard boot contract: path/hash compatibility, 20-file manifest, pre-parse and deferred executor")
