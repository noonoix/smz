#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
sidecar = root / "portable/plan3/CIRCUITPY/random_package_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
sidecar_text = sidecar.read_text(encoding="utf-8")

compile(entry_text, str(entry), "exec")
compile(sidecar_text, str(sidecar), "exec")
loader_pos = entry_text.index('import live_light_guard as _guard_bundle')
assert entry_text.index('if not hasattr(_real_os, "path"):') < loader_pos
assert "class _PathCompat:" in entry_text
assert 'sys.modules["os"] = _OsCompat()' in entry_text
assert '_real_os.stat(path)' in entry_text
assert entry_text.index('if not hasattr(_real_hashlib, "sha256"):') < loader_pos
assert "class _Sha256Compat:" in entry_text
assert "class _HashlibCompat:" in entry_text
assert '_real_hashlib.new("sha256")' in entry_text
assert 'def hexdigest(self):' in entry_text
assert 'sys.modules["hashlib"] = _HashlibCompat()' in entry_text
assert 'CircuitPython hashlib has no SHA-256 implementation' in entry_text
assert '("pico-calibration.json", "README-FLASH.md")' in entry_text
extras_pos = entry_text.index('for _name in ("pico-calibration.json", "README-FLASH.md"):')
load_pos = entry_text.index('_BOOT_BUNDLE = _guard_bundle.load_guard_bundle("/")')
assert loader_pos < extras_pos < load_pos
assert entry_text.count('.load_guard_bundle("/")') == 2
assert 'class _DeferredPlanEngine:' not in entry_text
assert 'sys.modules["plan_engine"] = _DeferredPlanEngine()' not in entry_text
assert 'from random_package_runtime import run_file_package' in entry_text
assert 'from random_package_runtime import run_parallel_group' in entry_text
assert 'def _light_parallel_group(' not in entry_text
assert 'def run_parallel_group(' in sidecar_text
assert 'def _light_goto_label(fh, args):' in entry_text
assert 'elif op == "LABEL":' in entry_text
assert 'elif op == "GOTO":' in entry_text
assert '"PGROUP"' in entry_text
assert 'elif op == "PGROUP":' in entry_text
runtime_pos = entry_text.index('import combined_guard_runtime as runtime')
assert load_pos < runtime_pos
assert 'gc.collect()' in entry_text[load_pos:runtime_pos]
init_start = entry_text.index("def _memory_safe_init(self):")
init_end = entry_text.index("runtime.Combined.__init__ = _memory_safe_init")
init_text = entry_text[init_start:init_end]
assert "bundle = _BOOT_BUNDLE" in init_text
assert "_ensure_runtime_bundle" in init_text
assert "_BOOT_BUNDLE = None" in init_text
assert "self.guard.bundle = bundle" in init_text
assert init_text.index("self.bundle = bundle") < init_text.index("runtime.Arm()")
assert "from combined_guard_runtime import main" in entry_text
assert "main()" in entry_text
print("Golden Pico boot contract: compatibility shims, pre-parse, deferred RPKG/PGROUP runtime, and bounded route executor")
