#!/usr/bin/env python3
"""Static guard for the C# settings, bindings and Persian Play Options UI."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
settings = (root / "ams-shell/src/Ams.UI/Services/DocumentService.cs").read_text(encoding="utf-8")
view_model = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycle.cs").read_text(encoding="utf-8")
ui = (root / "ams-shell/src/Ams.UI/MainWindow.AutoCycleUi.cs").read_text(encoding="utf-8")
expected = {
    "RestartMinMinutes": "110",
    "RestartMaxMinutes": "130",
    "AutoResumeMinMinutes": "3",
    "AutoResumeMaxMinutes": "5",
    "PostRestartTaskbarSlot": "1",
    "PostRestartLaunchBeforeMinSeconds": "1",
    "PostRestartLaunchBeforeMaxSeconds": "3",
    "PostRestartLaunchAfterMinSeconds": "20",
    "PostRestartLaunchAfterMaxSeconds": "40",
}
for name, default in expected.items():
    assert f"public int {name} {{ get; set; }} = {default};" in settings, (name, default)
    assert f"public int {name}" in view_model, name
    assert f"nameof(MainViewModel.{name})" in ui, name
assert "public bool AutoResumeEnabled { get; set; } = true;" in settings
assert "public bool AutoResumeEnabled" in view_model
assert "nameof(MainViewModel.AutoResumeEnabled)" in ui
assert "public bool PostRestartLaunchEnabled { get; set; } = true;" in settings
assert "public bool PostRestartLaunchEnabled" in view_model
assert "nameof(MainViewModel.PostRestartLaunchEnabled)" in ui
assert "Restart Launch" in ui and "Taskbar" in ui
assert 'public const string PortableBuzzerPin = "GP6";' in settings
assert "PortableBuzzerPinText" in view_model and "PortableBuzzerPinText" in ui
assert "NormalizeAutoCycleSettings" in settings
assert "SaveAutoCycleOptions" in view_model
assert "چرخه‌ی خودکار پیکو" in ui
assert "UpdateSourceTrigger.LostFocus" in ui
assert '"GP5"' not in settings + view_model + ui
print("app settings, bindings and UI: 35 passed, 0 failed")
