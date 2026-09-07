# CLAUDE-IMPLEMENT v0.9.58 — Keypad + green tests + self-containment fixes

Build on the **v0.9.57 source** (the one with `PortablePaths.cs` and the bundled `bridge/` Python stack). v0.9.57 shipped the self-containment work well, but a source review found **4 gaps** — including that it was published with **9 red tests**. This release finishes the job. Do NOT change the serial protocol, crypto, UART pins, or step behavior.

## Fix 1 — The 9 stale version-pin test failures (release-blocking)

`test-output-v0.9.57.txt` shows `671 passed, 9 failed`. All 9 are old test families asserting the CURRENT version with stale pins — exact labels:

- `v0.9.45: app version, banner and Pico bundle version match`
- `v0.9.46: app version, banner and Pico bundle version match`
- `v0.9.47: app version, banner and Pico bundle version match`
- `v0.9.48: app version, banner and Pico bundle version match`
- `v0.9.49: app version, banner and Pico bundle version match`
- `v0.9.50→51: app version, banner and Pico bundle version match`
- `v0.9.52: version pins for this release (csproj + banner + bundle)`
- `v0.9.55: version pins for this release (csproj + banner + bundle)` ×2 (two asserts share this label)

These pins are release bookkeeping, not behavior under test — bump every one to the new version (`<Version>0.9.58</Version>`, `Classroom Studio v0.9.58`, `BundleVersion = "0.9.58"`). **Never publish with a red test again.**

**Meta guard (prevents this class forever):** add a step-58 assertion that reads `tests/TestRunner.cs` itself (same repo-relative resolution the step-57 bridge tests use), regexes all `0\.9\.(\d+)` literals in it, and fails listing the line numbers if any pinned minor is older than the current version.

## Fix 2 — csproj must package the WHOLE bridge folder

The v0.9.57 csproj copies only `bridge.py` — `grep ams_serial Ams.UI.csproj` = **0 hits**. The release zip has `ams_serial.py`/`ams_crypto.py`/`serial/` only because they were copied by hand, so a clean `dotnet build`/publish loses the Python stack and Connect breaks again — exactly the fragility v0.9.57 was meant to kill. Replace the single-file bridge entry with:

```xml
<None Include="..\..\bridge\**"
      Link="bridge\%(RecursiveDir)%(Filename)%(Extension)"
      CopyToOutputDirectory="PreserveNewest" />
```

Keep the caterina/tools entries. After `dotnet build -c Release`, verify `bin\Release\net8.0-windows\bridge\ams_serial.py`, `ams_crypto.py` and `bridge\serial\__init__.py` exist next to the exe.

## Fix 3 — bridge.py: make brain-first REAL (docstring currently lies)

`detect_board_port()` carries the new brain-first docstring ("prefers the one answering role=brain…") but the body is still the old first-PONG-wins loop — there is **no `role=brain` check in the code**, and a duplicate leftover v0.9.5 docstring sits under the new one. Replace the whole function with exactly this:

```python
def detect_board_port():
    """v0.9.58 — brain-first auto-detect: probe every port with PING; prefer the one
    answering role=brain/pico-light (the Pico DATA port). The Pico console/REPL port
    never says PONG, so the twin-port trap (e.g. COM3 console vs COM5 data) resolves
    itself. Falls back to the old behaviour (first responder / best-scored port) when
    no Pico answers, so a lone Pro Micro still works."""
    try:
        from serial.tools import list_ports
        import serial
    except Exception:
        return None
    KNOWN = {(0x1A86, 0x7523), (0x1A86, 0x5523), (0x0403, 0x6001), (0x10C4, 0xEA60),
             (0x2341, 0x0043), (0x2341, 0x0001), (0x2A03, 0x0043),
             (0x2E8A, 0x0005)}   # Raspberry Pi Pico (CircuitPython CDC console+data)
    KEYS = ("ch340", "ch341", "usb-serial", "usb serial", "arduino", "cp210", "ftdi",
            "uart", "pico", "circuitpython")
    def score(p):
        s = 0
        if (p.vid, p.pid) in KNOWN: s += 100
        d = ((p.description or "") + " " + (p.manufacturer or "")).lower()
        if any(k in d for k in KEYS): s += 50
        return s
    def probe(device):
        """'brain' = pico-light answer; 'ok' = any PONG/HELLO/OK; None = silent."""
        try:
            ser = serial.Serial(device, 115200, timeout=0.4, write_timeout=0.4)
            try:
                ser.reset_input_buffer(); ser.reset_output_buffer()
                ser.write(b"PING\n"); ser.flush()
                t0 = time.monotonic(); buf = b""
                while time.monotonic() - t0 < 0.9:
                    chunk = ser.read(64)
                    if chunk:
                        buf += chunk
                    else:
                        time.sleep(0.02)
                    if b"role=brain" in buf or b"pico-light" in buf:
                        return "brain"
                    if b"PONG" in buf or b"HELLO" in buf or b"OK" in buf:
                        return "ok"
            finally:
                ser.close()
        except Exception:
            return None
        return None
    cands = sorted(list_ports.comports(), key=score, reverse=True)
    fallback = None
    for p in cands:
        v = probe(p.device)
        if v == "brain":
            return p.device      # Pico brain found — use it even if the arm is attached
        if v and fallback is None:
            fallback = p.device
    if fallback is not None:
        return fallback
    return cands[0].device if cands and score(cands[0]) >= 50 else None
```

Keep the stage events and `sys.path.insert(0, os.path.dirname(...))` exactly as v0.9.57 has them. `python -m py_compile bridge.py` must pass.

## Change 4 — Hardware keypad on the Pico (wiring v6: BTN1=GP2, BTN2=GP3)

The user's 1×4 flat membrane keypad is wired: common → GND, key1 → GP2, key2 → GP3 (keys 3/4 → GP4/GP5 reserved). Today the firmware has zero button code (`grep digitalio PicoFirmwareExporter.cs` = 0 hits), so pressing the keys does nothing. Final user-chosen mapping: **key1 = Num Lock = Run/Stop · key2 = Scroll Lock = Pause/Resume**.

1. `PicoFirmwareExporter.BuildCodePy`: emit a button reader polled in the main loop AND inside every wait loop (WLUX waits included, so emergency stop always works):
   - `import digitalio`; `btn1 = digitalio.DigitalInOut(board.GP2)`, `btn2 = digitalio.DigitalInOut(board.GP3)`, each `.direction = digitalio.Direction.INPUT`, `.pull = digitalio.Pull.UP` (active-low to GND); comment that GP4/GP5 are reserved for keys 3/4.
   - 40 ms software debounce, fire on the PRESS edge only.
   - BTN1 → `kbd.send(Keycode.NUM_LOCK)`; BTN2 → `kbd.send(Keycode.SCROLL_LOCK)`.
2. App side (`GlobalHotkeyService`): IN ADDITION to the user-configured hotkeys, always register `VK_NUMLOCK (0x90)` → Run/Stop toggle and `VK_SCROLL (0x91)` → Pause/Resume. Never remove or override the user's own hotkeys. Startup log line: `کلیدهای سخت‌افزاری برد: NumLock=اجرا/توقف · ScrollLock=مکث/ادامه`.
3. Options dialog: when `RunStopHotkey`/`PauseResumeHotkey` are unset, default them to `Num Lock` / `Scroll Lock`, show them in the fields, persist on save — the mapping stays visible and re-bindable from inside the app. Add a Persian hint line: `دکمه‌های کیپد روی برد (GP2/GP3) همیشه Num Lock و Scroll Lock را می‌فرستند.`
4. Note in docs: pressing key2 toggles the host's Num Lock state — harmless but visible on keyboards with a numpad.

## Change 5 — Version bump 0.9.58 everywhere

`Ams.UI.csproj` `<Version>0.9.58</Version>` · banner `Classroom Studio v0.9.58` · `PicoFirmwareExporter.BundleVersion = "0.9.58"` · every version pin in TestRunner (Fix 1 covers the 9 stale ones; step 57's pins too).

## Tests — new step 58 (≥12 assertions, all must PASS)

1. csproj contains the `bridge\**` wildcard with `CopyToOutputDirectory` (not just bridge.py).
2. `bridge/bridge.py` body contains `role=brain` probe logic and `def probe(device):` — and exactly ONE docstring in `detect_board_port`.
3. `bridge.py` keeps `0x2E8A, 0x0005`, all four stage events, and the bundled-first `sys.path.insert`.
4. Exporter output contains `digitalio.DigitalInOut(board.GP2)`, `board.GP3`, `Pull.UP`, `Keycode.NUM_LOCK`, `Keycode.SCROLL_LOCK`, and the 40 ms debounce; button polling happens inside the WLUX wait loop too.
5. `GlobalHotkeyService` registers `0x90` and `0x91` in addition to configured hotkeys.
6. Options defaults `Num Lock` / `Scroll Lock` when unset + the Persian hint line exists.
7. The meta version-pin guard (Fix 1) exists and passes.
8. Version pins: csproj + banner + BundleVersion = 0.9.58.
9. Exported `code.py` smoke test compiles (py_compile) and contains the button section.

Target: previous 671 passing + the 9 fixed + step 58 → **`0 failed` is a hard requirement before publish.**

## Docs + release

- `docs/keypad-v0.9.58.md` (fa): wiring recap, mapping table, Num-Lock side-effect note.
- Update `docs/portable-v0.9.57.md`: bridge wildcard packaging + brain-first fix notes.
- `MEMORY.md`: v0.9.58 entry.
- `dotnet build -c Release` → 0 errors. TestRunner → `0 failed`.
- Produce BOTH `Classroom-Studio-v0.9.58-release.zip` (flat layout, bridge folder fully populated FROM THE BUILD OUTPUT, not by hand) and the source zip. Replace BUILD-ONLY.md.

## Do NOT

- No wire-protocol, crypto, UART-pin, or step-execution changes.
- Do not remove user-configured hotkeys; the 0x90/0x91 registrations are additive.
- Do not touch the device/keyboard identity lists or the Pico exporter beyond adding the button section.
- Do not publish with any red test — v0.9.57 shipped with 9, that must not repeat.

## Acceptance

1. Clean checkout → `dotnet build -c Release` → `bridge\` next to the exe contains the full Python stack automatically.
2. TestRunner ends `N passed, 0 failed`.
3. Exported `code.py` reads GP2/GP3 with pull-ups + debounce and sends Num Lock / Scroll Lock.
4. With Pico (console+data ports) AND Pro Micro attached, AUTO connects to the Pico data port and the identity line shows `role=brain`.
5. Release + source zips named v0.9.58.
