#!/usr/bin/env python3
"""Static guard for the C# app-settings side of the v0.9.67 contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
source = (root / "ams-shell/src/Ams.UI/Services/DocumentService.cs").read_text(encoding="utf-8")
expected = {
    "RestartMinMinutes": "110",
    "RestartMaxMinutes": "130",
    "AutoResumeMinMinutes": "3",
    "AutoResumeMaxMinutes": "5",
}
for name, default in expected.items():
    assert f"public int {name} {{ get; set; }} = {default};" in source, (name, default)
assert "public bool AutoResumeEnabled { get; set; } = true;" in source
assert 'public const string PortableBuzzerPin = "GP6";' in source
assert "NormalizeAutoCycleSettings" in source
assert "NormalizeMinuteRange" in source
assert '"GP5"' not in source
print("app settings contract: 9 passed, 0 failed")
