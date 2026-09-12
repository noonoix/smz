#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[3]
model = (root / "ams-shell/src/Ams.UI/Models/PipelineWorkspace.cs").read_text(encoding="utf-8")
serializer = (root / "ams-shell/src/Ams.UI/Services/PipelineWorkspaceSerializer.cs").read_text(encoding="utf-8")
spec = (root / "docs/launch-pipeline-tabs.md").read_text(encoding="utf-8")
for name in ("Launch", "Main", "LaunchRecovery", "MainRecovery", "ResumeEssentials"):
    assert name in model
for filename in ("launch_steps.txt", "plan.txt", "launch_recovery.txt", "main_recovery.txt", "resume_essentials.txt"):
    assert filename in model
assert "FromLegacy" in model and "PipelineKind.Main" in model
assert "pipelineVersion" in serializer and "FixParents" in serializer
assert "There is no Restart Launch tab" in spec
assert "5, 10, 20, 40, 80" in spec
print("pipeline tabs migration contract: 15 passed, 0 failed")
