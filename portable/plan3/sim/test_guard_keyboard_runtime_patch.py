#!/usr/bin/env python3
from pathlib import Path
import py_compile, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "tools" / "patch_combined_runtime_output.py"
SOURCE = ROOT / "firmware" / "pico-light-guard-1.0.0" / "code.py"
def main():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "code.py"
        shutil.copyfile(SOURCE, target)
        for _ in range(2): subprocess.run([sys.executable, str(PATCH), str(target)], check=True)
        text = target.read_text(encoding="utf-8")
        package_text = SIDECAR.read_text(encoding="utf-8")
        py_compile.compile(str(target), doraise=True)
        py_compile.compile(str(SIDECAR), doraise=True)
        assert text.count("def _run_light_route(owner, name):") == 1
        assert text.count("def _light_keycode(vk):") == 1
        # Golden Build 52 extends the bounded streaming command set with the
        # RPKG package container; verify the previously-passed keyboard subset
        # without requiring the obsolete exact set literal.
        for op in ("PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "KEY", "KDOWN", "KUP", "RPKG"):
            assert op in text
        assert "PKGITEM" in package_text and "ENDPKG" in package_text
        assert 'elif op == "KEY":' in text
        assert 'elif op in ("KDOWN", "KUP"):' in text
        assert 'self.keyboard.release_all()' in text
        assert 'raise ValueError("unsupported virtual key: %d" % vk)' in text
        assert 'EVT|DEBUG|STEP/KEY keys=%d hold=%d' in text
    print("Golden keyboard + Random Package runtime patch: PASS")
if __name__ == "__main__": main()
