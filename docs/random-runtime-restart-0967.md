# Random wall-clock runtime, humanized restart, and GP5 audio contract

Implementation line: `0.9.67` (draft)

## Runtime

- On each manual Start, choose one inclusive random duration in `6600..7800` seconds (110–130 minutes).
- Draw once only. Child plans and root repeats share that deadline.
- The timer is wall-clock from Start; Pause does not extend it.
- Deadline expiry must interrupt long `DELAY`, `KTEXT`, sensor waits, child plans, packages, and parallel branches.
- Deadline expiry is distinct from manual Stop, transport failure, parser error, and other aborts.
- Only natural deadline expiry may enter the restart tail.
- After restart, a new run starts manually with Num Lock.

## Restart safety and timing

Before the restart tail, release every tracked keyboard key and mouse button. Then use the Windows 11 English power menu:

`Win+X → Up → Up → Enter → Up → Enter`

Every key is emitted as separate `KDOWN`, ranged hold `DELAY`, and matching `KUP`. Every inter-key wait is also a fresh ranged `DELAY`; no fixed robotic cadence is used. The final Enter is sent only after the release-all guard.

This avoids creating a script, scheduled task, PowerShell process, command shell, or RunMRU entry. Windows still records a restart in the Event Log; this is low-footprint, not trace-free. The menu ordering must be hardware-tested on the target Windows 11 image.

## Portable audio

- Portable audio supports only `deviceBuzzer` compiled to `BEEP|frequency,duration`.
- Output is fixed to Pico `GP5`.
- MP3/WAV paths, Windows player macros, PC speaker mode, looping media, and output-device selection are blocking export errors.
- Accepted frequency range: `30..20000 Hz`; duration must be non-negative.

## Required integration gates

1. Wire the Play Options range fields into both C# and Python exporters.
2. Add deadline checks to the Pico gate and all interruptible primitives.
3. Add a dedicated deadline-expired signal and suppress restart for Stop/error/abort.
4. Embed the generated split runtime byte-for-byte in `PlanExporter.cs`.
5. Keep canonical/split runtime parity and memory budgets green.
6. Keep the PR draft until CI is `0 failed` and the Windows-menu sequence passes hardware testing.
