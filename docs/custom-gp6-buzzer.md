# Custom GP6 buzzer step

`Buzzer Beep` replaces `Play Audio` in the insertion UI. Existing `playAudio` rows remain readable and executable in PC mode for backward compatibility.

The buzzer is passive and is driven only by Pico `GP6` through the hardware contract in issue #32. Presets are `short`, `double`, `warning`, `success`, and `custom`.

Custom syntax is `frequency:duration,pause;frequency:duration` in Hz/ms, for example `900:150,80;1200:250`. Each tone exports as `BEEP|freq,ms`; pauses export as `DELAY|ms`. Valid frequencies are 30–20000 Hz.
