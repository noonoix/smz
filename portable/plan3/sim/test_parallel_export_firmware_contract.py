#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[3]
exporter=(root/'ams-shell/src/Ams.UI/Services/PlanExporter.cs').read_text()
arm=(root/'firmware/arm28/ams_board26_impl.h').read_text()
runtime=(root/'portable/plan3/CIRCUITPY-MODERN/combined_guard_runtime.py').read_text()
executor=root/'portable/plan3/CIRCUITPY-MODERN/plan_engine_exec.py'
parallel=root/'portable/plan3/CIRCUITPY-MODERN/plan_engine_parallel.py'
bundle=(root/'ams-shell/src/Ams.UI/Services/ModernAutoCycleFirmwareBundle.cs').read_text()
assert '"forLoop" or "randomPackage"' in exporter
assert 'n.Type=="waitForSound"' in exporter
assert 'ParallelLeaf=new(){"randomMousePosition","mouseMove"' in exporter
# Keep the physically verified, near-capacity firmware unchanged.
assert '#define FW_VER   "2.8.1"' in arm
assert 'if (!strcmp(cmd, "SCAL"))' in arm
for token in ('def sound_start','def sound_poll','def sound_cancel','def type_char','SCAL|10'):
    assert token in runtime, token
assert parallel.exists() and parallel.stat().st_size > 8000
assert executor.stat().st_size < 20000, executor.stat().st_size
assert 'from plan_engine_parallel import run_parallel' in executor.read_text()
assert 'plan_engine_parallel.py' in bundle and 'manifestNames.Length != 25' in bundle
print('parallel export/firmware contract: 14 passed, 0 failed')
