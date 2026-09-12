# Launch Pipeline — browser-style step tabs

## Fixed tabs

1. **Launch** — shared by initial start and genuine Auto Resume.
2. **Main** — ordinary gameplay; resumes from the last safe checkpoint after reboot.
3. **Launch DC Recovery** — one complete retry attempt while entering the game.
4. **Main DC Recovery** — one complete retry attempt during Main.
5. **Resume Essentials** — resume-only preparation before restoring Main checkpoint.

The tabs are fixed and cannot be closed. Each tab owns an independent ordered step tree and dirty/validation state. Switching tabs loads that tab's tree into the editor; transient editor UI state such as current selection, collapsed rows and undo/redo stacks is reset on tab switch in this draft. `Ctrl+1` through `Ctrl+5` switch tabs.

## Launch order

Initial start:

`Windows Boot Guard → random delay → Win+slot → Launch → launch success check → Main from start`

Genuine Auto Resume:

`random delay → Win+slot → Launch → launch success check → Resume Essentials → Main from checkpoint`

There is no Restart Launch tab. The same Launch tree runs exactly once in either path.

## Export files

- `launch_steps.txt`
- `plan.txt`
- `launch_recovery.txt`
- `main_recovery.txt`
- `resume_essentials.txt`

Every file uses `PLAN|2`; only root `plan.txt` may carry AutoCycle directives.

## Migration

A legacy `.amsj` opens losslessly in the Main tab. The other four tabs begin empty. Saving upgrades the
document to the versioned pipeline envelope. The old marker/For Loop selection UI is removed only after
open/save/export round-trip tests pass.

## Recovery defaults

Both recovery profiles default to five attempts with exponential delays `5, 10, 20, 40, 80` seconds.
One attempt means one full execution of that recovery tab followed by a stable sensor success check.
After final failure, recovery returns without crashing; optional GP6 buzzer/error signalling is tracked as a hardware follow-up.
