#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
service = (root / "ams-shell/src/Ams.UI/Services/ResumeEssentialsContract.cs").read_text(encoding="utf-8")
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.ResumeEssentials.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.ResumeEssentialsUi.cs").read_text(encoding="utf-8")
assert 'MarkerProperty = "resumeEssentials"' in service
assert 'package.Props["mode"] = "shuffleAll"' in service
assert 'package.Props["minCount"] = package.Children.Count' in service
assert 'package.Props["maxCount"] = package.Children.Count' in service
assert "packages.Count > 1" in service
assert "Any(c => !c.IsDisabled)" in service
assert "MarkResumeEssentials" in vm and "ClearResumeEssentials" in vm
assert "Snapshot();" in vm and "MarkDirty();" in vm
assert "MarkResumeEssentialsCommand" in ui
assert "ClearResumeEssentialsCommand" in ui
assert "Shuffle All" in ui
print("C# Resume Essentials contract: 11 passed, 0 failed")
