#!/usr/bin/env python3
import json
from pathlib import Path
root = Path(__file__).resolve().parents[3]
helper = (root / 'ams-shell/src/Ams.UI/Services/AutoCycleFirmwareBundle.cs').read_text(encoding='utf-8')
vm = (root / 'ams-shell/src/Ams.UI/ViewModels/MainViewModel.AutoCycleFirmwareExport.cs').read_text(encoding='utf-8')
ui = (root / 'ams-shell/src/Ams.UI/MainWindow.AutoCycleFirmwareExportUi.cs').read_text(encoding='utf-8')
csproj = (root / 'ams-shell/src/Ams.UI/Ams.UI.csproj').read_text(encoding='utf-8')
manifest = json.loads((root / 'portable/plan3/autocycle_h6_patch.json').read_text(encoding='utf-8'))
base = (root / 'firmware/autocycle-hostusb-v5/code.pre-autocycle.py').read_text(encoding='utf-8')
expected = (root / 'firmware/autocycle-hostusb-v5/code.py').read_text(encoding='utf-8')
assert 'PicoFirmwareExporter.Export(' in helper
assert 'PatchManifest = "autocycle_h6_patch.json"' in helper
assert 'JsonSerializer.Deserialize<PatchDocument>' in helper
assert 'PropertyNameCaseInsensitive = true' in helper
assert 'RuntimeFiles.Append(PatchManifest)' in helper
assert '"resume_essentials_runtime.py"' in helper
assert 'PublishAtomically(payloads)' in helper
assert 'Distinct(StringComparer.OrdinalIgnoreCase)' in helper
assert 'autocycle_h6_patch.json' in csproj and 'resume_essentials_runtime.py' in csproj
assert 'AutoCycleFirmwareBundle.Export' in vm
assert 'ExportAutoCyclePicoFirmwareCommand' in ui
assert manifest['version'] == 1 and manifest['baseline'] in base
actual = base
for index, edit in enumerate(manifest['edits'], 1):
    assert actual.count(edit['old']) == 1, 'anchor %d is not unique' % index
    actual = actual.replace(edit['old'], edit['new'], 1)
assert actual == expected
for marker in ('AUTO_CYCLE_PATCH_0967_H6','import supervisor','import plan_cycle as _pc','EVT|HOSTUSB|','usb_down=_usb_host_down','_resume_boot.tick()','keypad: GP4 START accepted','0x10: Keycode.LEFT_SHIFT'):
    assert marker in actual and marker in helper
print('auto-cycle firmware integration + byte parity: 25 passed, 0 failed')
