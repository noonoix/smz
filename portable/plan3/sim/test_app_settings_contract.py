#!/usr/bin/env python3
"""Static guard for the C# settings and binding side of the v0.9.67 contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
settings = (root / "ams-shell/src/Ams.UI/Services/DocumentService.cs").read_text(encoding="utf-8")
view_model = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycle.cs").read_text(encoding="utf-8")
expected = {
    "RestartMinMinutes": "110",
    "RestartMaxMinutes": "130",
    "AutoResumeMinMinutes": "3",
    "AutoResumeMaxMinutes": "5",
}
for name, default in expected.items():
    assert f"public int {name} {{ get; set; }} = {default};" in settings, (name, default)
    assert f"public int {name}" in view_model, name
assert "public bool AutoResumeEnabled { get; set; } = true;" in settings
assert "public bool AutoResumeEnabled" in view_model
assert 'public const string PortableBuzzerPin = "GP6";' in settings
assert "PortableBuzzerPinText" in view_model
assert "NormalizeAutoCycleSettings" in settings
assert "SaveAutoCycleOptions" in view_model
assert '"GP5"' not in settings + view_model
print("app settings and bindings: 15 passed, 0 failed")
