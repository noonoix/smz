# v0.9.41 — spelling, marker veins, rail submenus, restart removal

Four user-reported items, all in the steps list / left rail / Play Options area.

## 1. Spelling (غلط املایی)

The row summary `Keystroke E · hold 88◆◆180ms` showed two replacement characters
(`U+FFFD`) instead of a dash. The source really did contain `U+FFFD`: an en dash had
been mangled during an earlier edit.

| File | Was | Now |
| --- | --- | --- |
| `Models/StepDefinitions.cs` | `hold {hmin}U+FFFDU+FFFD{hmax}ms` | `hold {hmin}–{hmax}ms` |
| `Services/HumanMouse.cs` | `cadence U+FFFDU+FFFD the stats` (comment) | `cadence — the stats` |
| `Services/RunEngine.cs` | mangled `───` divider (comment) | clean divider |

The hold range now matches the delay column, which already used `{Delay}–{DelayMax}`.
One Persian typo was fixed too: the light rail tooltip said `انتطار` instead of `انتظار`.

A repository-wide sweep now guards this: **no source file may contain `U+FFFD`**
(Step 41, assertions 1–2).

## 2. A toggle means children, and children mean a vein

The rule the user stated: *if a row has an accordion toggle, it has sub-steps, and if it
has sub-steps it must also draw a vein.*

`FlatStepRow.ShowToggle` was already correct (`HasChildren || an If/Else head`), so an
`# Else` row that owned sub-steps did show a toggle — but pressing it drew nothing,
because `Renumber()` only ever registered a scope range for the **scope head**
(`findImage` / `waitForSound` / `waitForLight` with `insertIfElse`). Marker rows
(`# Else`, `# End If`) were never keys in `_scopeRanges`, so `TryGetScopeRange` failed
and the overlay bailed out.

Fix, inside the marker-consumption loop of `Renumber()`:

```csharp
int markerStart = FlatSteps.Count;   // v0.9.41
AddRow(m, m.Number, depth, inner);
...
if (m.Children.Count > 0 && !_collapsed.Contains(m))
    WalkList(m.Children, m.Number + ".", depth + 1, inner);

// a toggle means children, and children mean a vein: a marker row that owns
// sub-steps is a scope of its own and registers its own range
if (m.Children.Count > 0) _scopeRanges[m] = (markerStart, FlatSteps.Count - 1);
```

Consequences:

* Pressing the toggle on `# Else` reveals a vein that spans **only the Else branch**,
  nested inside the If → End If bracket.
* `# End If` still has no children, so it still has no toggle and no vein — consistent
  with the rule.
* The v0.9.40 contract is untouched: `ToggleCollapse` already calls `FocusScopeVein(n)`
  for whatever node was toggled, marker rows included, and the overlay still resolves
  its range from `ScopeVeinNode`.

## 3. Random restart during play — removed

The user schedules the reboot externally (Task Scheduler, 110–130 min), so the in-app
option is gone rather than merely hidden:

* `MainWindow.xaml` — the whole Play Options row (checkbox + min/max boxes).
* `ViewModels/MainViewModel.cs` — `RandomRebootEnabled` / `Min` / `Max`, the
  `Task.Run` scheduler with `shutdown /r /t 0`, and the `rebootTask?.Wait(500)` in the
  run loop's `finally`.
* `Services/DocumentService.cs` — the three persisted settings fields.

`ShutdownWhenFinished` and `NoActivateWhenStopped` are untouched. Older settings files
that still carry the three keys simply ignore them.

## 4. The vertical rail now carries the whole Insert tab

The rail offered 11 quick-add buttons while the Insert tab offered 23 step types, so 12
types were menu-bar-only. The rail is now generated in 12 sections, each owning a
submenu for its own category; a `▾` caret marks a section that has sub-entries (the same
"caret means children" idea as the step rows).

| Section | Default click | Submenu |
| --- | --- | --- |
| Mouse | Mouse Click | Mouse Click, Mouse Position, Mouse Scroll, Random Mouse Position |
| Keys | Keystroke | Keystroke, Type Text, Key Down, Key Up |
| Image | Find Image | — |
| Sound | Wait For Sound | — |
| Light | Wait For Light | — |
| Loop | For Loop | For Loop, Run in Parallel (group) |
| RndPkg | Random Package | — |
| Delay | Delay | — |
| Note | Comment | Comment, Raw Command |
| Audio | Play Audio | — |
| Run | Run Exe | Run Exe, Open File / Program, Play Script (.amsj) |
| Label (new) | Insert Label | Insert Label, Go To Label |

23 types, all reachable from the rail. A `ScrollViewer` wraps the stack so the 12th
section stays reachable on short windows. Clicking the caret runs
`RailSubmenu_PreviewMouseLeftButtonDown`, which opens that button's `ContextMenu` to the
right and swallows the click so the default step is *not* added; right-clicking a
section opens the same submenu. Menu items bind through
`PlacementTarget.DataContext.AddStepCommand`, the same pattern the steps-list context
menu already used. The handler fully qualifies `System.Windows.Controls.Button` and
`System.Windows.Controls.Primitives.PlacementMode` because the project also references
Windows Forms.

## 5. Two stale assertions repaired

The real v0.9.40 build reported `400 passed, 3 failed`. All three were test bugs, not
product bugs, and all three are green in v0.9.41:

| Failing assertion | Cause | Fix |
| --- | --- | --- |
| `v0.9.25: every step field has a Persian entry (135 fields, 2 missing)` | v0.9.39 put `waitForLight:key/holdMin/holdMax` in the shared `Fa` table, where `Has()` can never match a step-qualified key | keys moved into `FaByStep` |
| `v0.9.34: banner bumped` | hard-coded `"v0.9.34"` | now checks `"Classroom Studio v0.9."` |
| `v0.9.38: the overlay asks ... Else row of the selected scope` | v0.9.40 moved the overlay to `ScopeVeinNode` | assertion follows `ScopeVeinNode` |

## Test coverage

Step 41 adds 15 assertions (384 `Assert(` lines in total): the `U+FFFD` sweep, the en
dash, the Persian tooltip, the `FaByStep` placement plus a live `StepTextsFa.Has` check,
the marker-range registration, the complete removal of the restart feature, the rail
coverage of all 23 Insert types, the six section submenus, the caret handler, and the
version/banner pair.
