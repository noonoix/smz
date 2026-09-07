# v0.9.49 — direction-aware plain-row drops + docked Options dialog

Two user reports from the v0.9.48 build, two root causes.

## 1) A middle-band drop on a plain row could silently no-op

Report (with screenshot): dragging `Key Down A` (row 1.2) onto `Type text` (row 1.1, a plain,
non-container row) did nothing, while the reverse worked. Root cause: the middle band of a
non-container row resolved to `mode = "into"`, and `MoveNode` fell back to `list.Insert(i + 1, …)` —
for the row directly below the target that index is its own current slot, so the "move" put the row
back where it started. The reverse direction inserted after the target, a real change — hence the
asymmetry the user saw.

Fix, two layers:

- `StepsList_Drop` (view): only containers and Else rows keep the three-band geometry (top quarter =
  before, middle = into, bottom quarter = after). Plain rows now split **50/50** — the dead middle band
  is gone. (`canInto = StepDefinitions.AcceptsChildren(target) || MainViewModel.IsElseMarkerRow(target)`.)
- `MoveNode` (view model): before the removal loop shifts indices, it captures the drag direction
  (`sameSiblings`, `nodeIdxBefore`, `targetIdxBefore`); a residual `"into"` on a plain row then resolves
  by direction through the new public static `DropBeforeForPlainRow` — dragging **up** inserts before the
  target, dragging **down** inserts after it. Cross-list drops keep the previous after-behaviour.
  All v0.9.48 marker-row redirects (Next / End If / Else / scope head) are untouched and still apply first.

## 2) The Options dialog floats; it should attach to the main window

The dialog already had an `Owner` and was modal, but `CenterOwner` left it floating in the middle of a
large window — once the v0.9.48 collapse fix made it compact, it looked like a loose card. Now
`OnSourceInitialized` docks it: `WindowStartupLocation.Manual`, `SizeToContent.Manual`, positioned flush
with the owner's right edge at the owner's top, full owner height (clamped into the work area). The XAML
keeps `SizeToContent="Height"` as the no-owner fallback, and the layout gains a `*` / `Auto` row split so
the OK/Cancel bar pins to the bottom of the docked window. No control names or tab logic changed.

## Tests

Step 49 = 10 deterministic assertions (5 behavioural for the drop rule incl. the exact reported case, 4
source-level guards, 1 version family). `Assert(` total: 479 → 489.
