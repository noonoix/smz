# ARM 2.7 — Phase 3A human mouse

Flash `ams_board27.ino` to the Pro Micro with `human_mouse_v3.h` beside it and the existing `arm26` directory preserved.

New framed brain-link commands:

- `HCFG|speedMin,speedMax,moveMin,moveMax,curveMin,curveMax,beforeMin,beforeMax,afterMin,afterMax`
- `HPAUSE|midChance,midMin,midMax,idleEveryMin,idleEveryMax,idlePauseMin,idlePauseMax,overChance`
- `HMOVE|x,y`
- `HRANDOM|x,y,w,h`

`HCFG` deliberately leaves the profile unarmed. Only a valid following `HPAUSE` makes movement executable. All ranges remain separate and are sampled inclusively. Movement is curved, acceleration/deceleration shaped, overshoot/correction capable, pause-aware and HALT-abortable. Legacy arm26 commands and encrypted USB behavior remain available.

This is Phase 3A. Pico dispatch and seeded parity vectors are the next gate before replacing the old RMOUSE/MOVETO path.
