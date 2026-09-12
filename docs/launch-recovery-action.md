# Launch DC Recovery action

While authoring the **Launch** pipeline tab, the Flow actions now expose **Run/Call Launch DC Recovery** in all three insertion surfaces: the Insert menu, the left-rail submenu, and the step-list right-click menu.

The action uses the existing `callLaunchDcRecovery` pipeline contract. Export converts it to `INCLUDE|file=launch_recovery.txt`; it is an execution transfer, not an editor-tab switch. The item is disabled outside the Launch tab, and the view model also rejects stale or programmatic insertion in another tab.
