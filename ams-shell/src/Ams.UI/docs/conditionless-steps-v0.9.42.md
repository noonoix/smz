# v0.9.42 — a step without a condition adopts nothing

## The user report

In `daroon1`, step **6.5.1 `Find image · 75% · entireScreen · timeout never`** had no condition
(`insertIfElse = false`), yet three rows (`6.5.1.1 Wait for light`, `6.5.1.1.1 Key Down ENTER`,
`6.5.1.2 Key Up ENTER`) were nested **under** it. They must sit **outside**, at the same level as
6.5.1. Second point: in the original program a Find Image step **without** a condition is called
*«جستجو برای تصویر» (search for image)*, not *«Find image»*. The same nesting bug happens under
**Wait For Light**.

## Root cause

`StepDefinition.IsContainer` / `IsScopeContainer` are flags of the **step type**, and
`findImage`, `waitForSound`, `waitForLight` all carry `IsContainer = true` so that the If/Else
machinery (§3.3.1) works. Every insert path asked the **type**, never the **node**:

| path | old check |
| --- | --- |
| Insert / rail / Insert-tab | `StepDefinitions.Get(sel.Type).IsContainer` |
| Paste | `StepDefinitions.IsContainer(selected.Type)` |
| Drag & drop “into” | `StepDefinitions.Get(target.Type).IsContainer` |

So selecting a conditionless Find Image (or Wait For Light) and inserting a step made that step a
**child**, and `Renumber()` then rendered it one indent level deeper — a Then branch that does not
exist. The runner has no branch to execute there either, so the visual and the semantics disagreed.

## The fix

### 1. Containership became a property of the node (`Models/StepDefinitions.cs`)

```csharp
public static bool IsConditionalContainer(string type)
    => type is "findImage" or "waitForSound" or "waitForLight";

public static bool OpensIfElse(StepNode n)
    => IsConditionalContainer(n.Type) && PropEx.GetBool(n.Props, "insertIfElse");

public static bool AcceptsChildren(StepNode n)
    => Get(n.Type).IsContainer && (!IsConditionalContainer(n.Type) || OpensIfElse(n));

public static bool IsScopeContainerNode(StepNode n)
    => Get(n.Type).IsScopeContainer && (!IsConditionalContainer(n.Type) || OpensIfElse(n));
```

For Loop, Random Package and Parallel Group are unconditional containers and keep their old
behaviour.

### 2. All three insert paths ask the node (`ViewModels/MainViewModel.cs`)

`InsertNode`, `Paste` and the drag-and-drop “into” mode now use `StepDefinitions.AcceptsChildren(node)`.
No type-only container check is left on any insert path (guarded by a test).

### 3. Old plans are repaired on open (`Services/DocumentService.cs`)

```csharp
public static int LiftOrphanChildren(IList<StepNode> list, StepNode? parent = null)
```

Recursively lifts every child of a conditionless head out so it becomes the **next sibling**, order
preserved, parent pointers fixed. `Else` / `End If` marker rows are skipped — they are the real
not-found branch and legitimately own children. It runs on **Open**, on **AMK import**, and after
**Edit** (so unchecking *Insert If-Else* releases the former branch instead of hiding it). A file
repaired on open stays dirty until saved, and the log line reports how many rows were released.

### 4. Naming (`Models/StepDefinitions.cs`, findImage `Summarize`)

| condition | before | after |
| --- | --- | --- |
| `insertIfElse = false` | `Find image · 75% · entireScreen · timeout never` | `Search for image · 75% · entireScreen · timeout never` |
| `insertIfElse = true` | `If Find image · …` | `If image found · …` |

`waitForLight` / `waitForSound` already switch their wording on the condition
(`Wait for light …` / `If Light …`), so only their nesting behaviour changed.

## Tests (Step 42 — 15 new assertions)

1–5 node-level containership for findImage / waitForLight / waitForSound and the unconditional
containers · 6–7 the two summary names · 8–9 three orphan rows are released in order at the right
level · 10–11 a real If head, its Else marker and the light step behave correctly · 12–14 the three
insert paths and the migration wiring · 15 version/banner.

Expected: `=== Results: 433 passed, 0 failed ===`

## Visual check after building

1. Open `daroon1.amsj`: the three rows under 6.5.1 now sit at 6.5.2 / 6.5.3 / 6.5.4, same indent as
   the search step, and the log reports the released rows.
2. Step 6.5.1 reads **Search for image · 75% · entireScreen · timeout never** and shows **no** toggle
   and **no** vein.
3. Select it and press Insert → the new step lands **after** it, not inside it.
4. Tick *Insert If-Else* → the row becomes **If image found · …**, an Else / End If pair appears and
   the toggle/vein come back. Untick it → the branch is released to the outer level.
5. Same four checks for **Wait For Light (BH1750)**.
