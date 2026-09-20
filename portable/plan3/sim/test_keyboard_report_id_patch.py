#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "tools" / "patch_keyboard_report_id.py"
SOURCE = ROOT / "firmware" / "pico-light-guard-1.0.0" / "combined_guard_runtime.py"


def main():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "combined_guard_runtime.py"
        shutil.copyfile(SOURCE, target)
        for _ in range(2):
            subprocess.run([sys.executable, str(PATCH), str(target)], check=True)
        text = target.read_text(encoding="utf-8")
        py_compile.compile(str(target), doraise=True)
        assert text.count("self.device.send_report(self.report, 1)") == 1
        assert "except TypeError:" in text
        assert text.count("def _send(self):") == 1
    print("keyboard report-id patch: PASS")


if __name__ == "__main__":
    main()
