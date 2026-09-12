# Orphan conditional marker repair

The editor treats `Else` and `End If` rows as structural markers owned by one live `insertIfElse` condition. Structural edits and legacy files can no longer leave duplicate or nested markers stuck in the tree.

The repair pass runs after edit, delete, cut, paste, and drag/move, and during open/import. It keeps every valid owned pair, removes unowned markers, lifts children from an orphan `Else` into the same sibling list, and then heals missing markers for active conditions. Repaired files remain dirty until the user saves them.

This preserves user steps and keeps corrupted older `.amsj` documents loadable.
