# Post-Restart Launch

## Contract

Root AutoCycle plans add one root-only directive:

`POSTLAUNCH|enabled,taskbarSlot,beforeMinSec,beforeMaxSec,afterMinSec,afterMaxSec`

Defaults: `POSTLAUNCH|1,1,1,3,20,40`.

On a genuine Auto Resume only, the Pico executes this ordered preamble before Resume Essentials:

1. release all held keys/buttons;
2. wait the configured before range;
3. press `Win+<slot>` with independent humanized modifier/key hold gaps;
4. wait the configured application-start range;
5. execute Resume Essentials;
6. execute the root plan.

Manual GP4 starts never run Restart Launch. The directive is root-only and is not copied into `resume_essentials.txt` or child includes.

## Restart quiescence invariant

When `plan_cycle.run_root()` returns `expired`, firmware must immediately set `engine_on = False`, release held input, and continue only `_resume_boot.tick()` plus keypad polling. It must never begin another plan pass while Windows is shutting down. A later validated HOSTUSB `DOWN/SUSPEND → UP`, stability window, and Auto Resume delay are the only path that calls `_auto_start_root()` and re-enables the engine.
