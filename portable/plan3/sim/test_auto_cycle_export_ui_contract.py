#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycleExport.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.CombinedGuardExportUi.cs").read_text(encoding="utf-8")
legacy_plan_ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleExportUi.cs").read_text(encoding="utf-8")
legacy_firmware_ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleFirmwareExportUi.cs").read_text(encoding="utf-8")
essentials_ui = (root / "ams-shell/src/Ams.UI/MainWindow.ResumeEssentialsUi.cs").read_text(encoding="utf-8")
schedule_ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleUi.cs").read_text(encoding="utf-8")
kit = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleStyles.cs").read_text(encoding="utf-8")
tabs_ui = (root / "ams-shell/src/Ams.UI/MainWindow.PipelineTabsUi.cs").read_text(encoding="utf-8")

assert "[RelayCommand]" in vm
assert "ExportCombinedPortableGuard" in vm
assert "PortableGuardBundle.Export" in vm
assert "AutoCyclePlanBundle.DecorateRoot" in vm
assert "SHA256.HashData" in vm
assert "CapturePipelineWorkspaceForExport" in vm
assert "PlanExporter.PlanBlockedException" in vm
assert "ExportCombinedPortableGuardCommand" in ui
assert "PlayOptBody" in ui
assert "ساخت بسته کامل چرخه + Macro + Guard" in ui
assert "ExportAutoCyclePicoPlanCommand" not in legacy_plan_ui
assert "ExportAutoCyclePicoFirmwareCommand" not in legacy_firmware_ui
assert "EnsureExportCard" in ui and "Reorder(body)" in ui
assert "EnsureAdvancedPanel(body)" in essentials_ui and "EnsureAdvancedPanel(body)" in schedule_ui
assert "Restart Launch" in schedule_ui and "PostRestartLaunchEnabled" in schedule_ui
assert "PostRestartTaskbarSlot" in schedule_ui and "BuildRangeRow" in schedule_ui
assert "MinHeight = 34" in kit and "MinWidth = 188" in kit
assert "#5E9FE8" in kit and "ReorderExportSteps" in kit
assert "PipelineTabs" in tabs_ui
print("single combined AutoCycle + Macro + Guard export contract: 26 passed, 0 failed")
