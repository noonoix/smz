#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[3]
exporter=(root/'ams-shell/src/Ams.UI/Services/PlanExporter.cs').read_text()
arm=(root/'firmware/arm28/ams_board26_impl.h').read_text()
runtime=(root/'portable/plan3/CIRCUITPY-MODERN/combined_guard_runtime.py').read_text()
assert '"forLoop" or "randomPackage"' in exporter
assert 'n.Type=="waitForSound"' in exporter
assert 'ParallelLeaf=new(){"randomMousePosition","mouseMove"' in exporter
# Keep the physically verified, near-capacity firmware unchanged.
assert '#define FW_VER   "2.8.1"' in arm
assert 'if (!strcmp(cmd, "SCAL"))' in arm
for token in ('def sound_start','def sound_poll','def sound_cancel','def type_char','SCAL|10'):
    assert token in runtime, token
print('parallel export/firmware contract: 10 passed, 0 failed')
