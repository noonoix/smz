#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
helper = (root / "ams-shell/src/Ams.UI/Services/AutoCycleFirmwareBundle.cs").read_text(encoding="utf-8")
vm = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycleFirmwareExport.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleFirmwareExportUi.cs").read_text(encoding="utf-8")
assert "PicoFirmwareExporter.Export(" in helper
assert "import plan_cycle as _pc" in helper
assert "ResumeArmStore" in helper and "AutoResumeBoot" in helper
assert "_pc.parse_cycle_plan(text)" in helper
assert "_pc.run_root(_plan_cache, _PlanCtx(), arm_store=_resume_store)" in helper
assert "usb_cdc.console.connected" in helper
assert "_resume_boot.tick()" in helper
assert "btn1 is not None and not btn1.value" in helper
assert "_resume_store.clear()" in helper
assert "def release_all(self):" in helper
assert "def kdown(self, vk):" in helper and "def kup(self, vk):" in helper
assert "AutoCycleFirmwareBundle.Export" in vm
assert "ExportAutoCyclePicoFirmwareCommand" in ui
print("auto-cycle firmware integration: 13 passed, 0 failed")
