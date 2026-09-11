#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycleExport.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleExportUi.cs").read_text(encoding="utf-8")
assert "[RelayCommand]" in vm
assert "ExportAutoCyclePicoPlan" in vm
assert "AutoCyclePlanBundle.Export" in vm
assert "_currentFile ?? \"untitled\"" in vm
assert "PlanExporter.PlanBlockedException" in vm
assert "ExportAutoCyclePicoPlanCommand" in ui
assert "PlayOptBody" in ui
assert "چرخه‌ی خودکار" in vm and "چرخه‌ی خودکار" in ui
print("auto-cycle export UI: 8 passed, 0 failed")
