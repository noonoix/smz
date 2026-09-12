#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[3]
contract = (root / "ams-shell/src/Ams.UI/Services/LaunchStepsContract.cs").read_text(encoding="utf-8")
bundle = (root / "ams-shell/src/Ams.UI/Services/AutoCyclePlanBundle.cs").read_text(encoding="utf-8")
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.LaunchSteps.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.LaunchStepsUi.cs").read_text(encoding="utf-8")
assert 'MarkerProperty = "launchSteps"' in contract
assert 'group.Type != "forLoop"' in contract
assert "LaunchStepsContract.Validate(steps)" in bundle
assert '"launch_steps.txt"' in bundle
assert "CompileOnce(launch.Children.ToList()" in bundle
assert "CloneWithoutLaunchGroup" in bundle
assert "MarkLaunchStepsCommand" in ui and "ClearLaunchStepsCommand" in ui
assert "LaunchStepsStatus" in vm and "OnPropertyChanged" in vm
print("launch steps contract: 8 passed, 0 failed")
