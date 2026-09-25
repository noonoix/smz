from pathlib import Path

root = Path(__file__).resolve().parents[1]
code = (root / "CIRCUITPY-MODERN" / "code.py").read_text(encoding="utf-8")
assert 'def _prepare_calibration_heap(self):' in code
assert 'proxy.module = None' in code
for name in ('plan_engine_exec', 'plan_engine_human', 'plan_engine_parse'):
    assert name in code
assert code.count('_prepare_calibration_heap(self)') == 4
assert 'self.samples = []\n        _prepare_calibration_heap(self)' in code
print('calibration heap release contract: PASS')

service = (root.parents[1] / "ams-shell" / "src" / "Ams.UI" / "Services" / "ModernAutoCycleFirmwareBundle.cs").read_text(encoding="utf-8")
assert '_prepare_calibration_heap' in service
assert 'CAL|heap-ready' in service
print('Classroom Studio calibration export contract: PASS')
