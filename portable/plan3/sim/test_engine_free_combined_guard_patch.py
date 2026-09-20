#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[3]
engine_free = root / "tools" / "patch_engine_free_combined_runtime.py"
main_patch = root / "tools" / "patch_combined_runtime_output.py"
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    entry = td / "code.py"
    runtime = td / "combined_guard_runtime.py"
    shutil.copyfile(root / "firmware/pico-light-guard-1.0.0/code.py", entry)
    shutil.copyfile(root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py", runtime)
    subprocess.run([sys.executable, str(main_patch), str(entry)], check=True)
    for target in (entry, runtime):
        subprocess.run([sys.executable, str(engine_free), str(target)], check=True)
        subprocess.run([sys.executable, str(engine_free), str(target)], check=True)
        py_compile.compile(str(target), doraise=True)
    entry_text = entry.read_text(encoding="utf-8")
    runtime_text = runtime.read_text(encoding="utf-8")
    assert "_DeferredPlanEngine" not in entry_text
    assert 'sys.modules["plan_engine"]' not in entry_text
    assert "import plan_engine" not in runtime_text
    assert "def _run_light_route(owner, name):" in entry_text
    assert "runtime.Combined.route = _diagnostic_route" in entry_text
print("engine-free Combined Guard import boundary: PASS")
