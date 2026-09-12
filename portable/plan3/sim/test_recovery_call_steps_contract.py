#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
defs = (root / "ams-shell/src/Ams.UI/Models/RecoveryCallStepDefinitions.cs").read_text(encoding="utf-8")
bundle = (root / "ams-shell/src/Ams.UI/Services/PipelinePlanBundle.cs").read_text(encoding="utf-8")

assert 'CallMain = "callMainDcRecovery"' in defs
assert 'CallLaunch = "callLaunchDcRecovery"' in defs
assert 'Label = "Run/Call Main DC Recovery"' in defs
assert 'Label = "Run/Call Launch DC Recovery"' in defs
assert 'Fields = Array.Empty<FieldDef>()' in defs
assert 'PipelineKind.Main' in bundle and 'PipelineKind.Launch' in bundle
assert 'INCLUDE|file=main_recovery.txt' in bundle
assert 'INCLUDE|file=launch_recovery.txt' in bundle
assert 'NormalizeRecoveryCalls' in bundle
assert 'فقط در تب Main مجاز است' in bundle
assert 'فقط در تب Launch مجاز است' in bundle
print("explicit recovery call steps: 11 passed, 0 failed")
