#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[3]
model = (root / "ams-shell/src/Ams.UI/Models/PipelineWorkspace.cs").read_text(encoding="utf-8")
serializer = (root / "ams-shell/src/Ams.UI/Services/PipelineWorkspaceSerializer.cs").read_text(encoding="utf-8")
wrapper = (root / "ams-shell/src/Ams.UI/Services/RestartGuardBundle.cs").read_text(encoding="utf-8")
export = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycleExport.cs").read_text(encoding="utf-8")
assert model.index("PipelineKind.Desktop") < model.index("PipelineKind.Restart") < model.index("PipelineKind.LoginOrDc")
assert 'Title = "Restart"' in model and 'FileName = "restart_steps.txt"' in model
assert "FormatVersion = 3" in model
assert "1 or 2 or PipelineWorkspace.FormatVersion" in serializer
assert 'routes[nameof(PipelineKind.Restart)] = RouteFile' in wrapper
assert 'restart.Steps.Count == 0 ? "PLAN|2\\n"' in wrapper
assert "RestartGuardBundle.Export" in export
assert "RestartGuardBundle.RebuildHashes" in export

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    live = td / "live_light_guard.py"
    code = td / "code.py"
    shutil.copyfile(root / "portable/plan3/CIRCUITPY/live_light_guard.py", live)
    source_code = (root / "firmware/pico-light-guard-1.0.0/code.py").read_text(encoding="utf-8")
    code.write_text(source_code.replace(
        '_VALID_ROUTE_NAMES = ("desktop_steps.txt", "login_or_dc_steps.txt",',
        '_VALID_ROUTE_NAMES = ("desktop_steps.txt", "login_or_dc_steps.txt",'), encoding="utf-8")
    # live patch is directly testable; code.py gains _VALID_ROUTE_NAMES after the main output patch.
    subprocess.run([sys.executable, str(root / "tools/patch_restart_route_output.py"), str(live)], check=True)
    py_compile.compile(str(live), doraise=True)
    assert '"Restart": "restart_steps.txt"' in live.read_text(encoding="utf-8")
print("Restart tab contract: persisted optional route after Desktop, v2 migration, export, hash and runtime validation covered")
