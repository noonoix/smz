from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one match in {path}, got {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")

vm = "ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs"

# Repair after editing can disable/remove ownership while preserving child steps.
replace_once(vm,
'''        DocumentService.LiftOrphanChildren(Steps);   // v0.9.42 — unchecking Insert If-Else releases the former branch

        Renumber();
''',
'''        DocumentService.LiftOrphanChildren(Steps);   // v0.9.42 — unchecking Insert If-Else releases the former branch

        RepairOrphanConditionalMarkers(Steps);

        HealMissingElseMarkers(Steps);

        Renumber();
''')

# Repair after delete and cut, before the flat projection is rebuilt.
replace_once(vm,
'''        SelectedNodes = new();

        SelectedNode = null;

        Renumber();

        MarkDirty();

        Log($"deleted {deletable.Count} step(s)");
''',
'''        SelectedNodes = new();

        SelectedNode = null;

        RepairOrphanConditionalMarkers(Steps);

        HealMissingElseMarkers(Steps);

        Renumber();

        MarkDirty();

        Log($"deleted {deletable.Count} step(s)");
''')
replace_once(vm,
'''        SelectedNodes = new();

        SelectedNode = null;

        Renumber();

        MarkDirty();

        Log($"cut {cuttable.Count} step(s)");
''',
'''        SelectedNodes = new();

        SelectedNode = null;

        RepairOrphanConditionalMarkers(Steps);

        HealMissingElseMarkers(Steps);

        Renumber();

        MarkDirty();

        Log($"cut {cuttable.Count} step(s)");
''')

# Paste and drag/move can import or relocate malformed legacy structures.
replace_once(vm,
'''        foreach (var loop in nodes.Where(n => OwnsNextMarker(n)))

            EnsureLoopMarker(loop);   // v0.9.45 — old/single-node clipboards receive # Next too

        Renumber();
''',
'''        foreach (var loop in nodes.Where(n => OwnsNextMarker(n)))

            EnsureLoopMarker(loop);   // v0.9.45 — old/single-node clipboards receive # Next too

        RepairOrphanConditionalMarkers(Steps);

        HealMissingElseMarkers(Steps);

        Renumber();
''')
replace_once(vm,
'''        if (OwnsNextMarker(node)) EnsureLoopMarker(node);   // v0.9.48 — a moved block always keeps its # Next row
        Renumber();
''',
'''        if (OwnsNextMarker(node)) EnsureLoopMarker(node);   // v0.9.48 — a moved block always keeps its # Next row
        RepairOrphanConditionalMarkers(Steps);
        HealMissingElseMarkers(Steps);
        Renumber();
''')

# Open/import: sanitize corrupt legacy files immediately and keep the document dirty for an explicit save.
replace_once(vm,
'''            int sanitized = SanitizeAllElseMarkers();   // v0.9.36 — a repaired file must remain dirty until saved

            int healed = HealAllElseMarkers();   // v0.9.37 — an If without Else/End If is invalid; repair on open
''',
'''            int orphaned = RepairOrphanConditionalMarkers(Steps);   // remove stuck orphan Else/End If rows and lift their children

            int sanitized = SanitizeAllElseMarkers();   // v0.9.36 — a repaired file must remain dirty until saved

            int healed = HealAllElseMarkers();   // v0.9.37 — an If without Else/End If is invalid; repair on open
''')
replace_once(vm,
'''            _dirty = sanitized > 0 || healed > 0 || loopHealed > 0 || lifted > 0;
''',
'''            _dirty = orphaned > 0 || sanitized > 0 || healed > 0 || loopHealed > 0 || lifted > 0;
''')
replace_once(vm,
'''            SanitizeAllElseMarkers();   // v0.9.35 — clean v0.9.33-era duplicate pairs on import

            HealAllElseMarkers();   // v0.9.37 — imports must land with complete If/Else structure
''',
'''            RepairOrphanConditionalMarkers(Steps);   // clean stuck orphan markers before healing active conditions

            SanitizeAllElseMarkers();   // v0.9.35 — clean v0.9.33-era duplicate pairs on import

            HealAllElseMarkers();   // v0.9.37 — imports must land with complete If/Else structure
''')

# Add the pure, recursive repair core before the existing all-tree sanitizer.
anchor = '''    /// <summary>v0.9.35 — after open/import: clean orphan duplicate marker pairs for every insertIfElse If

    /// in every sibling list (the v0.9.33 bug left them in old plans).</summary>

    private int SanitizeAllElseMarkers()
'''
method = '''    /// <summary>Repairs a sibling tree after structural edits or legacy-file load.

    /// Only marker objects owned by a live insertIfElse head survive. Children of an orphan

    /// Else are lifted into the same sibling list at the marker's position, so repair never

    /// destroys user steps. Returns the number of removed marker rows.</summary>

    public static int RepairOrphanConditionalMarkers(IList<StepNode> list)

    {

        int removed = 0;

        foreach (var n in list.ToList())

            if (n.Children.Count > 0) removed += RepairOrphanConditionalMarkers(n.Children);

        var owned = new HashSet<StepNode>();

        for (int i = 0; i < list.Count; i++)

        {

            var head = list[i];

            if (!IsIfElseHead(head)) continue;

            var (elseIndex, endIfIndex) = LocateElseMarkersForUi(list, i);

            if (elseIndex >= 0 && endIfIndex > elseIndex)

            {

                owned.Add(list[elseIndex]);

                owned.Add(list[endIfIndex]);

            }

        }

        for (int i = 0; i < list.Count;)

        {

            var marker = list[i];

            bool isConditionalMarker = IsElseMarker(marker) || IsEndIfMarker(marker);

            if (!isConditionalMarker || owned.Contains(marker)) { i++; continue; }

            list.RemoveAt(i);

            var parent = marker.Parent;

            var children = marker.Children.ToList();

            marker.Children.Clear();

            foreach (var child in children)

            {

                child.Parent = parent;

                list.Insert(i++, child);

            }

            removed++;

        }

        return removed;

    }



''' + anchor
replace_once(vm, anchor, method)

# Regression fixture mirrors the reported duplicate/nested orphan pattern.
test = "tests/TestRunner.cs"
insert_at = '''        // ── Step 14: v0.8.2 — native embedded-picture extraction (.amk BMPN) ──
'''
new_test = '''        // ── orphan conditional markers: repair after move/delete and legacy load ──
        var orphanHead = new StepNode
        {
            Type = "waitForLight",
            Props = new Dictionary<string, object?> { ["insertIfElse"] = true },
        };
        var ownedElse = MkComment("Else");
        var ownedEnd = MkComment("End If");
        var orphanElse = MkComment("Else");
        var preservedChild = MkComment("preserve me");
        orphanElse.Children.Add(preservedChild);
        orphanElse.Children.Add(MkComment("Else"));
        orphanElse.Children.Add(MkComment("End If"));
        var orphanEnd = MkComment("End If");
        var brokenConditionalRows = new List<StepNode>
            { orphanHead, ownedElse, ownedEnd, orphanElse, orphanEnd };
        int orphanRemoved = MainViewModel.RepairOrphanConditionalMarkers(brokenConditionalRows);
        Assert(orphanRemoved == 4,
            $"orphan repair removes duplicate and nested Else/End If rows (got {orphanRemoved})");
        Assert(brokenConditionalRows.Count == 4
               && ReferenceEquals(brokenConditionalRows[1], ownedElse)
               && ReferenceEquals(brokenConditionalRows[2], ownedEnd)
               && ReferenceEquals(brokenConditionalRows[3], preservedChild),
            "valid owned markers survive and orphan-Else children are lifted without data loss");
        Assert(ReferenceEquals(preservedChild.Parent, orphanHead.Parent),
            "lifted orphan-marker child receives the repaired sibling parent");

''' + insert_at
replace_once(test, insert_at, new_test)

Path("docs/orphan-conditional-marker-repair.md").write_text('''# Orphan conditional marker repair\n\nThe editor treats `Else` and `End If` rows as structural markers owned by one live `insertIfElse` condition. Structural edits and legacy files can no longer leave duplicate or nested markers stuck in the tree.\n\nThe repair pass runs after edit, delete, cut, paste, and drag/move, and during open/import. It keeps every valid owned pair, removes unowned markers, lifts children from an orphan `Else` into the same sibling list, and then heals missing markers for active conditions. Repaired files remain dirty until the user saves them.\n\nThis preserves user steps and keeps corrupted older `.amsj` documents loadable.\n''', encoding="utf-8")

Path(".github/workflows/apply-orphan-conditional-repair.yml").unlink()
Path(".github/scripts/apply_orphan_conditional_repair.py").unlink()
