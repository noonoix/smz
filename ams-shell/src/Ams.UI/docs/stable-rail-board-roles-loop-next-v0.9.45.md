# v0.9.45 — stable rail popup, visible board roles, structural Loop Next

## User reports

1. Rail submenus still stayed open after leaving and sometimes flickered until the app crashed.
2. The keyboard executor choice was not visible in Options.
3. For Loop needed the visible `Next` closing row used by the reference application, with the red vein closing on it.

## Fixes

### One rail popup state machine

The v0.9.43 implementation opened a WPF `ContextMenu` synchronously inside `MouseEnter`.
Opening the popup changes mouse capture and can synthesize another Enter/Leave cycle. v0.9.44
added independent `async void` leave delays, so several delayed close operations could race with
new opens. This produced the reported open/close flicker and eventual crash.

v0.9.45 replaces both behaviors with exactly two `DispatcherTimer` instances configured once:

- a 220 ms dwell timer opens one menu only if the same host is still hovered;
- a 120 ms watcher observes the combined region `host.IsMouseOver || menu.IsMouseOver` and closes
  after three outside ticks (about 360 ms);
- hover and ▾ click both call the same idempotent `OpenRailMenu`;
- one `CloseRailMenu` owns shutdown and the `Closed` event clears state;
- no `async void`, no `Task.Delay`, and no direct `menu.IsOpen = true` in `MouseEnter` remain.

### Dedicated Board Roles tab

The v0.9.44 controls existed, but they were in one horizontal row inside the 420 px Serial panel;
the second option could be clipped and the feature looked absent. Options is now 500 px wide and
has a fourth top-level tab, **تقسیم کار بردها**, with a dedicated vertical panel:

- Raspberry Pi Pico — brain, keyboard, light sensor;
- Arduino Pro Micro — arm, mouse, sound, keyboard.

The stored `KeyboardBoard` and its effect on exported `KBD_ON_ARM` are unchanged.

### Structural `# Next` for every For Loop

The runtime still iterates `forLoop.Children`; `Next` is intentionally visual/structural and does
not duplicate execution. Every loop now owns one immediate sibling comment marker named `Next`:

- created on Add and Edit;
- restored on Paste;
- recursively healed on Open and Import (`HealMissingLoopMarkers` / `HealAllLoopMarkers`);
- idempotent (a second healing pass inserts zero rows);
- protected from standalone Edit/Delete/Cut/Copy by `IsStructuralMarkerIn`;
- Loop + Next form one atomic destructive/clipboard unit, so removing/moving a loop cannot leave an
  orphan marker;
- `Renumber` already consumes `Next` through `IsScopeMarker`, therefore the red bracket now ends on
  the visible Next row, matching the supplied reference screenshots.

## Validation

- Step 45: 15 assertions; source total `Assert(` = 442.
- Expected real run: **480 passed / 0 failed** (v0.9.44 produced 465/0 + 15 new assertions).
- C# brace/paren/bracket balances: zero in every edited file.
- XML parse: MainWindow.xaml, OptionsDialog.xaml, Ams.UI.csproj — pass.
- Generated Pico code: timed/once/forever × keyboard-on-arm true/false — Python compile pass.
- U+FFFD sweep — zero.
