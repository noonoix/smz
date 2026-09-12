# Manual playback options

The editor keeps manual repeat controls only for deliberate local testing. The surface is named **Advanced manual run** and is collapsed by default so it does not permanently reduce the step list height.

- Normal **Run** uses the selected manual mode; the default remains one pass.
- Automated restart/resume timing belongs to **AutoCycle** and is not duplicated here.
- **Do not activate the main window when a script stops** is an application behavior setting under **Options → Behavior**.
- Saving execution logs lives beside the serial-log clear/copy actions.
- **Shut down the computer when repetition finishes** is retired from the UI and runtime. The legacy `ShutdownWhenFinished` JSON property remains readable so existing `ams-settings.json` files continue to load safely.

The legacy repeat properties remain part of exporter contracts; this cleanup does not change PLAN|2 or per-system firmware serialization.
