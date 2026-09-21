#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[3]
main_patch = root / "tools/patch_combined_runtime_output.py"
diag_patch = root / "tools/patch_guard_key_diagnostics.py"
source = root / "firmware/pico-light-guard-1.0.0/code.py"
with tempfile.TemporaryDirectory() as td:
    target = Path(td) / "code.py"
    shutil.copyfile(source, target)
    subprocess.run([sys.executable, str(main_patch), str(target)], check=True)
    for _ in range(2):
        subprocess.run([sys.executable, str(diag_patch), str(target)], check=True)
    text = target.read_text(encoding="utf-8")
    py_compile.compile(str(target), doraise=True)
    for marker in ("press-start", "press-index=", "press-ok=", "pressed", "release-start", "release-index=", "released", "cleanup-failed", "CLEANUP/keyboard", "CLEANUP/arm"):
        assert marker in text
    assert "primary = None" in text and "if primary is None:" in text
print("Guard keyboard diagnostics: per-key HID stages visible and cleanup cannot mask a primary route exception")
