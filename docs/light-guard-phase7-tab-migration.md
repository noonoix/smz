# Phase 7 — Seven-tab Guard workspace migration

## Visible workspace

Classroom Studio now defines seven visible pipeline tabs aligned with the six optical Guard positions plus one resumable workspace:

1. `Desktop`
2. `Login / DC`
3. `Character Dashboard`
4. `Entering Game / Loading`
5. `Game`
6. `Targeted`
7. `Resumable`

The tab names and order are canonical and match the Guard profile order, except that `Resumable` is the final non-optical workspace.

## Migration safety

The previous five-tab workspace (`Launch`, `Main`, `LaunchRecovery`, `MainRecovery`, `ResumeEssentials`) is not guessed into the new optical tabs. When an old workspace is opened:

- the seven new tabs start empty unless they already have canonical data;
- every old tree is preserved in `legacyPipelines` as migration backup;
- no old Step is silently deleted or reassigned;
- an explicit mapping review is required before legacy Steps can drive a new optical transition.

The saved workspace format is version 2 and retains the legacy backup alongside the seven visible trees.

## Execution boundary

The seven tabs establish the workspace structure only. They do not by themselves authorize automatic execution. The Guard-to-Step transition controller must use an explicit transition table, stable-state debounce, one-shot transition deduplication and an independent DC reason/context before any RunEngine integration is enabled.
