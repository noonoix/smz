#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")
tree = ast.parse(entry_text)

notes = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        if any(isinstance(target, ast.Name) and target.id == "_CAL_NOTES" for target in node.targets):
            notes = ast.literal_eval(node.value)
            break

assert notes == (262, 294, 330, 349, 392, 440)
assert len(notes) == 6 and len(set(notes)) == 6
assert all(30 <= note <= 20000 for note in notes)

assert "runtime.pwmio.PWMOut(runtime.board.GP6" in entry_text
assert "duty_cycle=32768" in entry_text
assert 'self.emit("ERR|CAL|AUDIO")' in entry_text
assert "tone.deinit()" in entry_text
assert "def _cal_position_tone" in entry_text
assert "def _cal_stage_complete_tone" in entry_text
assert "def _cal_complete_melody" in entry_text
assert "runtime.Combined.start_cal = _audible_start_cal" in entry_text
assert "runtime.Combined.next_cal = _audible_next_cal" in entry_text
assert "runtime.Combined.cal_tick = _audible_cal_tick" in entry_text
assert "runtime.Combined.save_cal = _audible_save_cal" in entry_text
assert "if self.calibrating and self.stage != previous:" in entry_text
assert 'was_sampling = self.result == "sampling"' in entry_text
assert "len(self.saved_ids) == len(runtime.PROFILES)" in entry_text

# Preserve the planned two-button responsibilities in the underlying runtime.
assert 'self.next_cal() if self.calibrating' in runtime_text
assert 'if yellow == "up" and not self.yellow.long: self.yellow_action()' in runtime_text
assert 'if self.result is not None: self.save_cal(); return' in runtime_text
assert 'self.result = "sampling"' in runtime_text

print("combined Guard audible six-position and two-button contract: PASS")
