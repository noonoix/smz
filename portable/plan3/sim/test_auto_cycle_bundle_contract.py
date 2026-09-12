#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
csproj = (root / "ams-shell/src/Ams.UI/Ams.UI.csproj").read_text(encoding="utf-8")
helper = (root / "ams-shell/src/Ams.UI/Services/AutoCyclePlanBundle.cs").read_text(encoding="utf-8")
for name in ("plan_cycle.py", "cycle_runtime.py", "restart_windows.py", "auto_resume_boot.py", "resume_essentials_runtime.py"):
    assert name in csproj
    assert name in helper
assert "CopyToOutputDirectory>PreserveNewest" in csproj
assert "PlanExporter.Export(" in helper
assert "ResumeEssentialsContract.Validate(steps)" in helper
assert "ResumeEssentialsContract.Find(steps)" in helper
assert "PlanExporter.CompileOnce" in helper
assert '"resume_essentials.txt"' in helper
assert '"RUNFOR|"' in helper and '"AUTORESUME|"' in helper
assert "settings.RestartMinMinutes" in helper and "settings.RestartMaxMinutes" in helper
assert "settings.AutoResumeMinMinutes" in helper and "settings.AutoResumeMaxMinutes" in helper
assert "PublishAtomically(payloads)" in helper
assert "Distinct(StringComparer.OrdinalIgnoreCase)" in helper
print("auto-cycle C# bundle: 21 passed, 0 failed")
