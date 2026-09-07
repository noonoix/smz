# v0.9.48 — Next everywhere, atomic drag unit, edge auto-scroll, collapsed Options tabs

Three user-reported problems, three root causes, one version.

## 1) Every child-capable block owns a `# Next` closing row

The user rule: *every section that can hold children must close with `# Next`, aligned with its head.*
v0.9.45 gave the marker only to For Loop; v0.9.48 extends it to **Parallel Group** and **Random Package**
via one helper — `OwnsNextMarker(type) = forLoop | parallelGroup | randomPackage` — used on the Add,
duplicate-Add, Edit, Paste and Open/Import-heal paths. If-family blocks keep their own Else/End If markers.
The marker is delete-protected (`IsStructuralMarkerIn`), part of the atomic clipboard/delete unit
(`ExpandConditionalSelection`), consumed by the vein walk (`IsScopeMarker`), and its text aligns with the
scope head structurally (shared `Depth`/`Indent` + the fixed 14 px toggle column — the v0.9.47 mechanism).

## 2) Drag & drop cannot leave a marker behind or detach one

- `MoveNode` now builds a **moveSet**: a container and its immediate `# Next` sibling are removed and
  re-inserted together (order preserved), so a dragged block always arrives whole; `EnsureLoopMarker`
  re-runs after the move so even a legacy marker-less block leaves with its closing row.
- **Marker-row drop targets resolve inside the block**, so no drop can detach a marker:
  - before / middle of a `# Next` or `# End If` row → appended at the end of the owning block's last branch
    (the Else branch when present, resolved by `FindClosingMarkerOwner(In)`);
  - just above an `# Else` row → end of the Then branch; just under it → start of the Else branch
    (`FindElseMarkerOwner(In)`); the v0.9.42 "into the Else row" behaviour is unchanged;
  - just under a scope head → its **first** child (a sibling insert there used to split the head from
    its closing row);
  - after a closing marker → after the whole block (already outside, marker stays attached).
- **Auto-scroll while dragging** (`StepsList_DragOver`): within 28 px of the top/bottom edge the list
  scrolls 14 px per DragOver tick via the ListBox's ScrollViewer (`FindDescendant<T>`). Without it a
  bottom row could never reach the top of a long plan — the user's "the move does not happen" report.

## 3) Options dialog fits the visible tab

Root cause of the "messy, long" board-role tab: inactive tab panels were `Visibility.Hidden`, which
**still reserves layout height** — with `SizeToContent="Height"` the window grew to the SUM of all four
tabs and the visible panel floated in dead space. All four panels are now `Collapsed` (code-behind +
XAML defaults). The board-role tab itself is redesigned as two option cards (title + one-line subtitle)
with a single concise note — top-anchored, no dead space. Control names (`KbdPicoRadio`, `KbdArmRadio`,
`GroupName="kbdBoard"`) are unchanged, so the code-behind logic is untouched.

## Tests

Step 48 = 13 deterministic assertions (6 behavioural via public statics, 6 source-level guards, 1 version
family). The v0.9.44 assertion that pinned the old "parallel groups have no closing marker" rule was
rewritten as a retraction assertion (same line count). `Assert(` total: 466 → 479.
