#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[3]
entry = root / "firmware/pico-light-guard-1.0.0/code.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
protocol_path = root / "ams-shell/src/Ams.UI/Services/LightGuardCalibrationProtocol.cs"
entry_text = entry.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")
protocol_text = protocol_path.read_text(encoding="utf-8")
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

patterns = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in (
                "_GUARD_START_PATTERN",
                "_GUARD_STOP_PATTERN",
                "_GUARD_PAUSE_PATTERN",
                "_GUARD_RESUME_PATTERN",
            ):
                patterns[target.id] = ast.literal_eval(node.value)

assert set(patterns) == {
    "_GUARD_START_PATTERN",
    "_GUARD_STOP_PATTERN",
    "_GUARD_PAUSE_PATTERN",
    "_GUARD_RESUME_PATTERN",
}
for pattern in patterns.values():
    audible = [note for note in pattern if note[0] > 0]
    total_duration_ms = sum(duration for _, duration in pattern)
    assert 3 <= len(audible) <= 6
    assert 850 <= total_duration_ms <= 1100
    assert all((frequency == 0 or 30 <= frequency <= 20000) and duration > 0 for frequency, duration in pattern)
assert len({patterns[name] for name in patterns}) == 4

assert "runtime.pwmio.PWMOut(runtime.board.GP6" in entry_text
assert "duty_cycle=32768" in entry_text
assert 'self.emit("ERR|CAL|AUDIO")' in entry_text
assert "tone.deinit()" in entry_text
assert "def _cal_position_tone" in entry_text
assert "def _cal_record_start_tone" in entry_text
assert "self._cal_beep(660, 65)" in entry_text
assert "runtime.Combined.cal_record_start_tone = _cal_record_start_tone" in entry_text
assert "self.cal_record_start_tone()" in entry_text
assert "def _cal_stage_complete_tone" in entry_text
assert "def _cal_save_success_tone" in entry_text
assert "self._cal_beep(880, 90)" in entry_text
assert "self._cal_beep(1320, 180)" in entry_text
assert "def _cal_complete_melody" in entry_text
assert "runtime.Combined.start_cal = _audible_start_cal" in entry_text
assert "runtime.Combined.next_cal = _audible_next_cal" in entry_text
assert "runtime.Combined.cal_tick = _audible_cal_tick" in entry_text
assert "runtime.Combined.save_cal = _audible_save_cal" in entry_text
assert "runtime.Combined.cal_save_success_tone = _cal_save_success_tone" in entry_text
assert "runtime.Combined.guard_start_tone = _guard_start_tone" in entry_text
assert "runtime.Combined.guard_stop_tone = _guard_stop_tone" in entry_text
assert "runtime.Combined.guard_pause_tone = _guard_pause_tone" in entry_text
assert "runtime.Combined.guard_resume_tone = _guard_resume_tone" in entry_text
assert "if self.calibrating and self.stage != previous:" in entry_text
assert 'was_sampling = self.result == "sampling"' in entry_text
assert "had_pending_result and self.saved" in entry_text
assert "not profile_was_saved" in entry_text

# Short blue presses wrap from the final calibration position back to Desktop,
# but never while sampling or while an unsaved result is pending.
assert "self.stage == len(runtime.PROFILES) - 1" in entry_text
assert 'self.result != "sampling"' in entry_text
assert "not (self.result is not None and not self.saved)" in entry_text
assert "self.stage = 0" in entry_text
assert 'self.emit("EVT|CAL|mode=ready|stage=1|id=" + runtime.PROFILES[0]' in entry_text

# Yellow explicitly owns first sample, save, and same-position retry.
assert "def _repeatable_yellow_action" in entry_text
assert 'if not self.calibrating:' in entry_text
assert 'if self.result == "sampling":' in entry_text
assert "if isinstance(self.result, dict) and not self.saved:" in entry_text
assert "self.save_cal()" in entry_text
assert "retry = 1 if self.saved and isinstance(self.result, dict) else 0" in entry_text
assert "self.samples = []" in entry_text
assert "self.sample_started = runtime.time.monotonic()" in entry_text
assert 'self.result = "sampling"' in entry_text
assert "|retry=%d" in entry_text
assert "runtime.Combined.yellow_action = _repeatable_yellow_action" in entry_text

# Board-owned Start/Stop/Pause/Resume controls have distinct rhythmic tones.
assert "def _guard_pattern" in entry_text
assert "def _guard_start_tone" in entry_text
assert "def _guard_stop_tone" in entry_text
assert "def _guard_pause_tone" in entry_text
assert "def _guard_resume_tone" in entry_text
assert "runtime.Combined._guard_pattern = _guard_pattern" in entry_text
assert "def _audible_buttons" in entry_text
assert "self.guard_start_tone()" in entry_text
assert "self.guard_stop_tone()" in entry_text
assert "self.guard_pause_tone() if self.controls.paused else self.guard_resume_tone()" in entry_text
assert "runtime.Combined.buttons = _audible_buttons" in entry_text
assert "_GUARD_STATUS_TONE_MS" not in entry_text

assert "self.blue_stop_consumed = False" in entry_text
assert "self.blue_start_consumed = False" in entry_text
assert "self.blue_start_pending = False" in entry_text
assert 'if blue == "down" and not self.calibrating and self.controls.running:' in entry_text
assert "self.blue_stop_consumed = True" in entry_text
assert "consumes the blue press" in entry_text
assert 'elif blue == "down" and not self.calibrating and not self.controls.running:' in entry_text
assert "def _immediate_audible_start" in entry_text
assert "self.immediate_audible_start()" in entry_text
assert "self.blue_start_pending = True" in entry_text
assert "self.blue_start_consumed = True" in entry_text
assert "def _enter_calibration_from_pending_start" in entry_text
assert "self.enter_calibration_from_pending_start()" in entry_text
assert 'not getattr(self, "blue_start_pending", False)' in entry_text
assert "runtime.Combined.immediate_audible_start = _immediate_audible_start" in entry_text
assert "runtime.Combined.enter_calibration_from_pending_start = _enter_calibration_from_pending_start" in entry_text
assert "runtime.Combined.loop = _audible_loop" in entry_text

# Physical button calibration and Classroom Studio calibration must keep the same math.
assert "spread > 5" in runtime_text
assert '"tolerance":max(2.0,spread*1.5)' in runtime_text
assert '"stable_ms":750' in runtime_text
assert "double maximumSpread = 5.0" in protocol_text
assert "Math.Max(2.0, spread * 1.5)" in protocol_text
assert "int stableDurationMs = 750" in protocol_text

# Live Classroom Studio must reach a Pico-local buzzer step without a Pro Micro.
assert "def _live_host_beep" in entry_text
assert 'reply = "OK|SETRES"' in entry_text
assert 'reply = "OK|BEEP"' in entry_text
assert "30 <= frequency <= 20000" in entry_text
assert "0 <= duration_ms <= 60000" in entry_text
assert "runtime.Combined._live_host_beep = _live_host_beep" in entry_text
assert "runtime.Combined.host_poll = _live_host_poll" in entry_text
assert 'reply = "ERR|EXEC|" + head' in entry_text
assert "role=brain" in entry_text

# Preserve the underlying two-button responsibilities.
assert 'self.next_cal() if self.calibrating' in runtime_text
assert 'if yellow == "up" and not self.yellow.long: self.yellow_action()' in runtime_text
assert 'if self.result is not None: self.save_cal(); return' in runtime_text
assert 'self.result = "sampling"' in runtime_text

print("combined Guard audible record start, save cue, cyclic positions, rhythmic Start/Stop/Pause/Resume tones, calibration parity and live buzzer contract: PASS")
