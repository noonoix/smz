# v0.9.43 — UI polish batch: seven user-reported items

User report (2026-09-04, on the v0.9.42 build) and the fix per item:

1. **"The vertical rail doesn't have all the Insert-tab items."** — Coverage check: the rail
   already carried all 23 step types (12 sections, 6 submenus). The real gaps found and fixed:
   the right-click **Add Action** menu was missing `parallelGroup`, `playAudio` and `runExe`,
   and on short windows the rail's bottom sections could sit below the fold — the rail is now
   more compact (padding 0,5→0,3, margin 4,2→4,1, icons 17→15). A Step-43 test now asserts
   rail == Insert tab == right-click menu as sets, so a future step type can't forget a menu.
2. **Submenus open on hover, not on caret click** — an `EventSetter MouseEnter →
   RailButton_MouseEnter` on the `RailButton` style opens the section's ContextMenu
   (Placement=Right); hovering a sibling closes the previous one. Guard: while keyboard focus
   is in a TextBox, hover never opens a menu (it would capture the keys). The ▾ caret click
   still works as a fallback.
3. **Serial log is clearable** — a "🧹 پاک‌سازی" button in the log expander header runs
   `ClearLogCommand` → `LogLines.Clear()` and prints `log cleared`.
4. **Undo/Redo "doesn't exist"** — it existed since v0.9.30 (Ctrl+Z/Y, 100-deep JSON
   snapshots) but was invisible. Now in the Edit menu: Undo Ctrl+Z / Redo Ctrl+Y.
5. **Manual Pico connect** — new status-bar port picker: editable ComboBox (AUTO default)
   + ⟳ refresh. Refresh asks bridge.py's new `list_ports` op for real ports
   ("COMx — description" labels). The picked port overrides the saved default;
   `MainViewModel.PortDeviceFromText` parses the bare device out of a label.
   `PythonBoardBridge` gained `EnsureProcess()` (ConnectAsync reuses it) and `ListPortsAsync()`;
   `IBoardBridge` has a default empty implementation so fakes/tests don't break.
   bridge.py changed → new sha256 (see BUILD-ONLY-v0.9.43.md).
6. **Hotkeys paired 4 → 2** — RunStop (default Shift+F1) toggles run/stop; PauseResume
   (default Shift+F3) toggles pause/resume. `GlobalHotkeyService` registers two IDs;
   `MainViewModel` adds `RunOrStop`/`PauseOrResume`; the Options dialog shows two capture
   rows; `AppSettings.Load()` migrates the four legacy keys once (run→runstop,
   pause→pauseresume; the old stop/resume keys are retired).
7. **Audio output device is a dropdown, not a number** — new `FieldKind.AudioDevice` +
   `StepDialog.MakeAudioDeviceCombo` lists NAudio WaveOut devices by name
   ("#0 — Speakers …"), storing the same int index as before. The Persian label keeps the
   v0.9.33 marker "-۱=خودکار".

Also repaired the one failing v0.9.42 test — the v0.9.37 assertion pinned the exact
`_dirty = sanitized > 0 || healed > 0;` source line, which v0.9.42 had legitimately extended
with `|| lifted > 0`. Assertion updated (deliberate change, documented here).

Tests: Step 43 adds 12 assertions (`Assert(` total 411). Expected: **446 passed / 0 failed**
(434 executed in the v0.9.42 run + 12).
