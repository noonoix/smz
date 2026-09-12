#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[3]
legacy = (root / "ams-shell/src/Ams.UI/Services/LaunchStepsContract.cs").read_text(encoding="utf-8")
bundle = (root / "ams-shell/src/Ams.UI/Services/PipelinePlanBundle.cs").read_text(encoding="utf-8")
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.PipelineTabs.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.PipelineTabsUi.cs").read_text(encoding="utf-8")
assert 'MarkerProperty = "launchSteps"' in legacy  # read-only migration compatibility
assert '"launch_steps.txt"' in bundle
assert "PipelineKind.Launch" in bundle
assert "CompileOnce" in bundle
assert "PipelineTabs" in ui and "SwitchPipelineCommand" in ui
assert "PipelineWorkspace" in vm and "CapturePipelineWorkspaceForExport" in vm
assert "FromLegacy" in (root / "ams-shell/src/Ams.UI/Models/PipelineWorkspace.cs").read_text(encoding="utf-8")
print("launch tab contract: 7 passed, 0 failed")
