# v0.9.47 - the structural `# Next` label aligns with its loop head

## Reported problem

The `# Next` text rendered further to the right than its own `For ... times` head row, so the
closing marker looked like a child of the loop instead of its sibling terminator. It has to sit
further out, exactly level with the head of the group.

## Root cause

v0.9.46 added a Next-only margin:

```csharp
public Thickness SummaryInset => Node.Type == "comment" && PropEx.GetString(Node.Props, "text") == "Next"
    ? new Thickness(12, 0, 0, 0) : new Thickness(0);
```

bound in the row template as `Margin="{Binding SummaryInset}"`. That single binding was the whole
12px offset.

The row template already guarantees alignment without any margin at all:

- the outer row grid uses `Margin="{Binding Indent}"` with `Indent => new(Depth * 22, 0, 0, 0)`;
- `# Next` is the loop's **sibling**, so it has the same `Depth` and therefore the same indent;
- inside `RowTextAnchor` the toggle occupies a **fixed** `ColumnDefinition Width="14"`, which stays
  reserved even when the toggle is hidden, so `SummaryText` of every row starts at the same x.

So the 12px was the only thing breaking alignment.

## Fix

- Removed the `SummaryInset` property from `FlatStepRow`.
- Removed the `Margin="{Binding SummaryInset}"` binding from the row template.
- Nothing else changed: row numbering, `Depth`, hierarchy and the red vein endpoint are untouched.
  The vein is still measured against the scope head's `SummaryText` and still closes on the Next row.

## Result

`# Next` now starts at exactly the same x as its `For ... times` head, one visual level outside the
loop body, which is what a sibling closing marker should look like.

## Test note

The two v0.9.46 assertions that pinned the 12px inset were rewritten as retraction assertions, so
Step 46 keeps its line count. Step 47 adds 9 deterministic assertions.
