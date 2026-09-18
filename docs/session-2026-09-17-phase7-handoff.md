# Phase 7 handoff — 2026-09-17

## Synchronization contract

This is the durable GitHub mirror of the live Notion session **«ادامه جلسه Classroom Studio — ۱۷ سپتامبر ۲۰۲۶»**. It records technical checkpoints, evidence, hashes, safety gates, fixes, and exact next actions. The full chat transcript is intentionally not copied. This file stays on `docs/session-2026-09-17-handoff` so documentation commits do not alter code-artifact provenance.

## Current state

- Active repository: `bermoods/smm`
- Original repository mirror source: `c4haztex/smc-1`
- Code branch: `phase7/light-guard-calibration`
- Old Draft PR: https://github.com/c4haztex/smc-1/pull/175 (PR metadata itself was not migrated; branch content was mirrored.)
- Last validated pre-migration code head: `388bc0551bb9196dcf2a2933b45d7f3d33ccbac3`
- Latest active branch head: `31ebd5645ac3cbf8a0cb3761fa6787e431fcf793`
- Latest functional code change: `31ebd5645ac3cbf8a0cb3761fa6787e431fcf793`
- Current Windows artifact run before migration: https://github.com/c4haztex/smc-1/actions/runs/35261951361
- CI: pre-migration head had 12 executable checks succeeded; post-migration cleanup has not yet produced a validated artifact.
- Installed hardware bundle remains `stage12`; it does not contain the latest calibration/control-audio changes.
- Board: COM30/COM31 hot-plug detected; COM31 automatically selected; `role=brain` confirmed.
- Hardware passed: Boot, control plane, compact light telemetry, `SETRES`, live Buzzer Step, calibration-entry cue, and stable Desktop sample-complete cue.
- Next package: export and validate a fresh package from run `35261951361`; use a new name such as `stage14.zip` to avoid confusing it with any package made from the previous run.

## Repository rescue and active remote

The old repository was mirrored to `bermoods/smm` after Actions on the old account became unavailable. The local rescue verified a complete Git bundle with 233 refs and pushed all normal branches and tags to the new private repository. GitHub-internal `refs/pull/*` refs were rejected by design and are not required because their source branches were preserved.

- New active repository: https://github.com/bermoods/smm
- New `main` after removing the temporary rescue workflow: `e064bfbcd8e7cf8ddb928d28bf41ea7826ae8316`
- New `phase7/light-guard-calibration` after removing the temporary rescue workflow: `3c97560ea0f0200543d4e9abd68d5100fb7e5f79`
- Functional code commit added before rescue cleanup: `2c2a9c8700ba617d6431b2b8410e4bb17765811c`
- Local offline rescue bundle verified by the user: `C:\Users\wasteland\repo-backups\smc-1-complete-rescue.bundle`

## Post-migration functional changes

The active Phase 7 branch now includes board-owned two-second feedback tones for the non-calibration controls:

- Guard Start: distinct two-second tone.
- Guard Stop/HALT: distinct two-second tone.
- Pause: distinct two-second tone.
- Resume: distinct two-second tone.

These tones are played by the Pico on GP6 and do not depend on the route engine or Arduino arm. The static audio contract test now also asserts these bindings. The Classroom Studio calibration protocol contract now includes a parity case proving the same median/spread/tolerance/stable-ms math used by physical button calibration: median center, reject spread over 5 lux, `tolerance=max(2.0, spread*1.5)`, and `stable_ms=750`.

## Fixed wiring and controls

- BH1750/GY-30: 3V3, GND, SDA=GP20, SCL=GP21, address `0x23`.
- GP4 blue square button: long hold enters/exits calibration; short press advances position; after position 6 it wraps to position 1 only when no sample or unsaved result is pending.
- GP3 yellow round button: held during boot for maintenance; inside calibration it starts sampling, saves a completed sample, and after a successful save can start a fresh sample for the same position.
- GP6: passive piezo.
- UART0 to arm: GP16 TX, GP17 RX, 57600 8N1, common ground.
- Light Watch must remain off during physical calibration; Classroom Studio may remain connected and green.

## Calibration profiles

1. `desktop` — 262 Hz
2. `login-or-dc` — 294 Hz
3. `character-dashboard` — 330 Hz
4. `entering-game-loading` — 349 Hz
5. `game` — 392 Hz
6. `targeted` — 440 Hz

Sampling uses a five-second window, median center, minimum five readings, maximum spread 5 lux, tolerance `max(2.0, spread * 1.5)`, and `stable_ms=750`.

## Final audio contract

- Position entry/advance/wrap: one 220 ms position-specific note.
- Yellow accepted for recording or re-recording: one short `660 Hz / 65 ms` cue immediately when sampling begins.
- Stable sample completed: two pulses of the current position note (`110 ms`, pause, `190 ms`).
- Save or re-save succeeded: ascending `880 Hz → 1320 Hz` success cue.
- First successful completion of all six profiles: six-note completion melody.
- Failed saves do not produce a success cue.

## Explicit yellow-button state machine

The yellow workflow is now implemented as explicit branches rather than relying on the legacy `result is not None` delegation:

1. If not calibrating, retain Pause/Resume behavior.
2. If already sampling, emit Busy and do not start a second sample.
3. If a completed unsaved dictionary result exists, save it.
4. Otherwise, begin a fresh sample explicitly:
   - `retry=0` for the first sample at that position;
   - `retry=1` when the same position had already been saved.
5. Emit the `mode=started` event and immediately play the short 660 Hz record-start cue.
6. During same-position retry, the previous persisted calibration remains valid. It is replaced only after the new sample completes and yellow is pressed again to save.

Expected sequence for a saved profile:

```text
short yellow → 660 Hz start cue
wait 5 seconds → double position-note completion cue
short yellow → 880→1320 Hz save-success cue
short yellow again → 660 Hz retry-start cue for the same position
```

## Relevant commits

| Commit | Change |
|---|---|
| `67ab1edf2cae12985d344ec37f5ad97a1b2071d0` | Filesystem persistence and GP3 maintenance contract. |
| `dd006a370bf6b43c17ed5f17709ca7815fd76ab5` | Calibration audio cues and six position notes. |
| `9d32e09bd6e53fc506f847bff3fc28ad1fa64a8c` | Compact light-response parser. |
| `a84849447fe6773dd1a006ec0e8582c1161c56c5` | Pico-local live `SETRES`/`BEEP` and GP6 output. |
| `88ff59fcbb8d6c0613e2f76ee77c9f9da766f893` | Buzzer-to-`BEEP/DELAY` Combined Guard route adapter. |
| `79b4618700bd5a275d6241363d1e00ba43573184` | Removed the second legacy export rejection path. |
| `1be2b9342bcdbb7be69bba6328dcbe665c6f8027` | Added save-success cue and safe profile-6-to-profile-1 wrap. |
| `172528e1fb2c1430ef03f7395c74f7e92a43a1f5` | First same-position retry implementation. |
| `388bc0551bb9196dcf2a2933b45d7f3d33ccbac3` | Reworked yellow into explicit sample/save/retry branches and added the 660 Hz record-start cue. |

Earlier Boot fixes remain in force: low-memory import ordering/deferred plan engine, CircuitPython `os.path` compatibility, 20-payload manifest alignment, and `hashlib.new("sha256")` compatibility.

## Bundle and hardware evidence

### `stage12`

- ZIP SHA-256: `6ad814f2311d9ee25c3d9554cf3d85410e8d696b11fee9b8a35c279265613c25`
- Exactly 21 files and 20 manifest entries.
- Zero hash mismatches, unsafe paths, or Python syntax errors.
- Installed successfully; live Buzzer Step passed.

```text
hot-plug: board detected on COM30, COM31 — connecting automatically
port_open: COM31
connected: ...|profiles=6|role=brain
→ SETRES|1920,1080
← OK|SETRES
→ BEEP|2637,66
← OK|BEEP
...
run finished
```

The user confirmed audible Buzzer output, calibration-entry audio, and the stable sample-complete alarm. Classroom Studio currently does not surface unsolicited physical-button `EVT|CAL|...` lines in its UI log, so audio is the immediate physical feedback.

## Diagnosis of “behavior did not change”

The board still runs a bundle without the latest workflow code unless a package exported from the corresponding new artifact is installed. Merely launching a newer Windows build does not update Pico firmware. The retry logic has now also been rewritten explicitly and covered by static contract tests, but hardware confirmation requires a newly exported and validated bundle.

## `stage13.zip` validation

The user provided `stage13.zip` from the migrated repository artifact flow. Validation passed.

- ZIP SHA-256: `c5e7332341d122e0b9f45fdabbc990df61924a08cf62a634b4c35336735c71ba`
- Exactly 21 files.
- No unsafe paths.
- `SHA256SUMS.txt`: 20 entries, 0 missing files, 0 hash mismatches.
- JSON files parse successfully: `guard-calibration.json`, `guard-transition.json`, `pico-calibration.json`.
- Generator: `Classroom Studio v0.9.67`.
- `hardwareCalibrationVerified: false`.
- Python syntax: 8 files, 0 syntax errors.
- `code.py` SHA-256: `1efde414f4b593c53345f6acac60ea5fa7a9b1ec6a24c99a24f11280cf7a6625`.
- `combined_guard_runtime.py` SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`.
- Runtime normalized size remains 20,200 bytes.
- No real `adafruit_hid` import and no `class Keycode`.
- Internal `Keyboard` and `release_all()` remain present.
- New audio contracts are present: record-start `660 Hz / 65 ms`, save-success `880 → 1320 Hz`, and distinct two-second Start/Stop/Pause/Resume tones.
- Same-position retry marker and final-position wrap are present.
- Pico-local host `BEEP` and `role=brain` remain present.

Important: the package's `guard-calibration.json` contains the exported/default calibration values with revision `guard-bf2929070db779e4`, not the five profiles physically saved on the board. A full copy of this package to `CIRCUITPY` would overwrite the board's current physical calibration. Before installing `stage13`, copy the current board `guard-calibration.json`, `guard-transition.json`, and `SHA256SUMS.txt` out of `CIRCUITPY` and validate/merge them, or intentionally accept resetting calibration.

## Rhythmic board-control audio update

The previous two-second continuous Start/Stop/Pause/Resume tones were replaced with short rhythmic signatures. This avoids a stuck-alarm feel and makes the four board-owned controls easier to distinguish.

- Commit: `4c14f7e422ff2c74f338d1aa7649cee0e5af7762`
- Start: rising 5-event pattern, about 880 ms total.
- Stop/HALT: descending 5-event pattern, about 920 ms total.
- Pause: repeated 3-note pattern with rests, about 900 ms total.
- Resume: rising/moving 5-note pattern, about 900 ms total.
- Static contract updated to require 3-6 audible notes per pattern, total duration 850-1100 ms, valid frequency range, four distinct patterns, and the existing Start/Stop/Pause/Resume bindings.
- Local static test passed before commit.
- PR #3 CI after commit: 12 executable checks succeeded; downloadable package skipped by branch condition. Main Windows artifact run: https://github.com/bermoods/smm/actions/runs/35283172213

The user log after replacing the previous package shows the board booting and connecting successfully on COM31 with `combined-pico-guard-executor|hid=on|uart=on|profiles=6|role=brain`. This confirms Boot/control-plane connectivity for the installed package, but the rhythmic update requires a new artifact/package from commit `4c14f7e...` before hardware audio confirmation.

## Immediate Stop on blue press

The user confirmed the rhythmic tones are good, but Stop only sounded after holding/releasing the blue button path. The cause was the previous short-press state machine: outside calibration, Start/Stop was triggered on blue-button release so it could be distinguished from a long hold. Stop is now treated as fail-safe and acknowledged immediately on button down while Guard is running.

- Commit: `d1bfaf7689beac560eae6ff0ba72c38fecc7a9cd`
- Behavior: when `controls.running` is true and GP4/blue goes down outside calibration, the firmware immediately calls `controls.stop()`, marks the press consumed, and plays the rhythmic Stop cue.
- The consumed press prevents the later release or long-hold path from accidentally restarting Guard or entering calibration.
- Start remains on short release while not running, so long hold can still enter calibration from idle.
- Static contract updated to assert the immediate down-trigger and consumed-press guard.
- PR #3 CI after commit: 12 executable checks succeeded; downloadable package skipped by branch condition. Main Windows artifact run: https://github.com/bermoods/smm/actions/runs/35284798949

The currently installed `stage14.zip` does not include this Stop-on-down fix; a fresh artifact/export package is required before hardware confirmation.

## Active safety gates

- Do not send `GUARD|ON`.
- Do not execute operational routes, macros, HID actions, or actuators.
- Do not create or copy `ams_key.json`.
- Keep PR #175 Draft; do not merge or release.
- Route serialization and first non-empty-route memory behavior remain separate unapproved gates.
- Do not continue real calibration on the old installed bundle.

## Exact next action

1. Continue from `bermoods/smm` on branch `phase7/light-guard-calibration`.
2. Download the new Windows artifact from run `35283172213`, produced after commit `4c14f7e422ff2c74f338d1aa7649cee0e5af7762`.
3. Export Combined Portable Guard into a clean staging folder.
4. Send the resulting archive with a new name such as `stage14-rhythm.zip` for provenance and content validation.
5. Do not copy anything to `CIRCUITPY`, do not send `GUARD|ON`, and do not continue hardware calibration until validation passes.


## `stage16.zip` validation and Stop hardware result

The user provided `light-state-windows-output(27).zip` and `stage16.zip`, produced after commit `4a4108b3d72eced92948b3eacd1735872c4d2b0f`.

### `light-state-windows-output(27).zip`

- ZIP SHA-256: `6c48bc598010de13231758fb690f4dbcb93e07a79fe7a33f268bc0db3246c3e2`
- 83 entries.
- No unsafe paths.
- Commit marker: `4a4108b3d72eced92948b3eacd1735872c4d2b0f`.
- Contains `_immediate_audible_stop`.

### `stage16.zip`

- ZIP SHA-256: `cfb73c1355db7ae6491e62a0e3cc08a7c94316412ec307b98c999951490d9831`
- 21 entries and no unsafe paths.
- All required runtime files are present.
- `SHA256SUMS.txt`: 20 entries, zero duplicate, missing, or mismatched hashes.
- JSON files parse successfully.
- Calibration revision: `guard-bf2929070db779e4`.
- `hardwareCalibrationVerified: false`.
- Python syntax: 8 files, zero errors.
- `code.py` SHA-256: `42a04d97f5ef12cee464779ca88e5cd851fa53e485e0dcbb8c593bd36cff90da`.
- `combined_guard_runtime.py` SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`.
- Runtime normalized size: 20,200 bytes.
- Confirmed contracts: immediate Stop helper, fail-safe state before Stop cue, keyboard release before Stop cue, Stop tone before `arm.abort()`, blue-down Stop trigger, consumed-press guard, host `GUARD|OFF`/`HALT` immediate path, rhythmic Start/Stop/Pause/Resume patterns, record/save/retry cues, `role=brain`, no `adafruit_hid`, no `class Keycode`.

Hardware result after installation: the user confirmed Stop is fixed.

## Immediate Start-on-press fix

New hardware report: Stop works, but Start requires two or three physical presses before the Start cue is heard. Root cause: Start still waited for a short blue-button release so it could be distinguished from the three-second long-hold calibration gesture.

The new fix makes Start audible on the first physical blue-button down while preserving calibration safety:

- Commit: `31ebd5645ac3cbf8a0cb3761fa6787e431fcf793`
- If GP4/blue goes down while not calibrating and Guard is not running, the firmware immediately resets the guard, starts the control state, marks the press as pending/consumed, and plays the rhythmic Start cue.
- Route execution is gated until the same press is released. This prevents a held Start press from triggering route execution before the firmware knows whether it is actually a long-hold calibration request.
- If that same press becomes a long hold, the pending Start is cancelled, fail-safe state is restored, and calibration entry happens directly with the position-1 cue.
- Stop remains immediate on blue-button down while Guard is running.
- The static audio contract was expanded to cover `blue_start_pending`, `blue_start_consumed`, immediate Start-on-down, pending-start cancellation into calibration, and route gating while Start is pending.
- Local syntax check and the focused static contract test passed before push.
- PR #3 CI after this commit completed: 12 executable checks succeeded; the downloadable test package check was skipped by branch condition.
- Artifact/run link for the new build: https://github.com/bermoods/smm/actions/runs/35286694567

## Updated exact next action

1. Download the new `light-state-windows-output` artifact from https://github.com/bermoods/smm/actions/runs/35286694567.
2. Export Combined Portable Guard into a clean staging folder and send the new package, e.g. `stage17-start-down.zip`, for validation.
3. Do not install it on `CIRCUITPY` until the package validation passes.
4. After install, verify Boot/control-plane first, then check that Start and Stop both sound on the first physical press.
5. Keep `GUARD|ON`, operational routes, HID actions, actuator execution, merge, and release blocked until the relevant gates are explicitly reopened.


## `stage17.zip` validation — Start-on-press fix

The user provided `stage17.zip` and `light-state-windows-output(28).zip` after the Start-on-press fix.

### Windows artifact

- File: `light-state-windows-output(28).zip`
- SHA-256: `8a2c43b08734105e8453a599f260e674ac8230b4449e78a0eed74d989796449e`
- 83 entries; zero unsafe paths.
- `ClassroomStudio.exe` is present.
- `LIGHT-STATE-TEST.txt` identifies source commit `31ebd5645ac3cbf8a0cb3761fa6787e431fcf793`.

### Pico package

- File: `stage17.zip`
- SHA-256: `3d0ed36443044255d44239c6a8d7a89b06b92f664d069261dde27632ba1af498`
- Exactly 21 entries; zero unsafe paths and duplicate names.
- Required payload files are present.
- `SHA256SUMS.txt`: 20 entries; zero missing, duplicate, or mismatched hashes.
- All 3 JSON files parse successfully; revision `guard-bf2929070db779e4` and `hardwareCalibrationVerified: false`.
- Python syntax: 8 files, zero errors.
- `code.py` SHA-256: `c256f7db5daac3fbcff8ef5bed9ce9689558301fc2df4cfbb0a4d4971d9e123f`.
- `combined_guard_runtime.py` SHA-256: `2b5007117b105c4b8fd24447036ca26c2e15557521cd7b22ed30e5a56c8e34f5`.
- Normalized runtime size: 20,200 bytes.
- Start-on-press, pending-start route gate, long-hold calibration handoff, immediate Stop, rhythmic cues, `role=brain`, internal keyboard driver, and no real `adafruit_hid` import are present.

### Installation gate

`stage17.zip` passed static validation and is approved for controlled installation. Preserve any real board calibration files before copying because the package still carries `hardwareCalibrationVerified: false` and export/default calibration metadata. Copy payload files first and `SHA256SUMS.txt` last; reboot; verify only `PING`, `LUX?`, and `CALGET` before any operational Guard or route test.


## Silent stop for read-only Light Watch

The user observed that clicking the Light Watch `توقف پایش` button played the Guard Stop cue. Diagnosis: `LightWatchService.StopCoreAsync` called the bridge-wide `SendAbortAsync`, which emits `HALT`; the Pico correctly plays the Stop cue for HALT, but read-only sensor polling must not change Guard state or make an alarm.

- Fix commit: `b4e551d60630223122f1478b3b465a30e9a1789d`.
- `LightWatchService` now cancels and awaits its read-only polling task without sending the global HALT/abort command.
- Actual Guard Stop remains unchanged and still acknowledges immediately with its Stop cue.
- CI run: https://github.com/bermoods/smm/actions/runs/35313991381
- CI result: all executable checks succeeded; downloadable package skipped by branch condition.

Next: download the Windows artifact from this run, export a new Combined Portable Guard package, send it for validation, then install only after validation passes. Do not use the current stage17 package to verify the silent-stop behavior.

## Current checkpoint — stage21 and calibration persistence

- `stage21.zip` was validated before installation: SHA-256 `dfacb8475b2861e26ba77260414488742b74cf6d899adf996041d6e57aea1ad0`; 21 entries, no unsafe paths, 20 manifest hashes with zero mismatch, and 8 Python files with valid syntax.
- The package contains the silent shutdown contract `HALT|SILENT`; the latest Windows CI run is [35317438521](https://github.com/bermoods/smm/actions/runs/35317438521) and is green.
- Combined Guard identity is now accepted and displayed correctly on COM31: `combined-pico-guard-executor`, role `brain`, 6/6 profiles.
- The user re-ran the six-position physical calibration. The application showed Pico revision `pending` while the program revision remained `guard-bf2929070db779e4`; this is not proof that calibration was persisted to CIRCUITPY.
- The latest files presented as board copies still contain the export/default values. `guard-calibration.json` SHA-256 is `0410aca5c16971ba65820c197ba8d2640d7b6db4697fcbdf0d4a167e54c15063`; profiles remain `desktop=0`, `login-or-dc=25`, `character-dashboard=31`, `entering-game-loading=5`, `game=26`, `targeted=20`, all with tolerance 2 and `stable_ms=750`.
- The matching `guard-transition.json` and `SHA256SUMS.txt` previously supplied also corresponded to those default values. If these files truly came from the CIRCUITPY root, physical calibration was not persisted or was overwritten; if they came from staging, the copy source was wrong.

<callout icon="⚠️" color="yellow_bg">
تا وقتی فایل واقعی calibration با مقادیر فیزیکی تأیید نشده است، Sync شش پروفایل، `GUARD|ON`، route عملیاتی، HID و actuator ممنوع بمانند. این checkpoint فقط نتیجهٔ بررسی persistence را ثبت می‌کند و موفقیت کالیبراسیون فیزیکی را تأیید نمی‌کند.
</callout>

### Exact next diagnostic

1. فقط profile `desktop` را دوباره کالیبره کن؛ پس از نمونه‌برداری و ذخیره، برنامه را نبند و Sync یا Export نکن.
2. بلافاصله `guard-calibration.json` را مستقیماً از ریشهٔ `CIRCUITPY` کپی کن و بفرست.
3. اگر مقدار `desktop.center` هنوز 0 بود، مشکل در persistence firmware است؛ اگر تغییر کرده بود، مشکل از مسیر copy/reboot یا staging قبلی بوده است.
4. پس از اثبات persistence، هر شش profile را تکرار، فایل‌ها را حفظ و سپس `CALGET`/Sync را بررسی می‌کنیم.

- درخواست UI کاربر برای انتقال تب وضعیت به header و پنجرهٔ جداگانه ثبت شد؛ اجرای آن بعد از حل persistence انجام می‌شود.


## Latest checkpoint — writable CIRCUITPY and six-profile persistence

The persistence investigation is now separated into two paths: physical Pico calibration and the Windows-side six-profile Sync action.

### Fixes and validated packages

- Persistence/read-back diagnostics: `17058d555ebaeebf0262204cb9bf6609441309ce`.
- `CALSTATUS` protocol and UI reporting: `29d7a431d7a18053e621ba19f37625c4404ce23d` and `ee86df1a57711eaa06fc28699dabfcade8fe438c`.
- Explicit writable CIRCUITPY remount and write verification: `b94a2257cf888af6ceef085eba17423a1a7c5371`.
- `stage26.zip` SHA-256: `7ca04ca560e95b5533b587952c14e02bc778be3ea1f0fd733890e064e0e62ca5`; 21 files, 20 manifest hashes, zero mismatches, no unsafe paths, valid Python syntax.
- Windows artifact `Classroom-Studio-final-fixes(2).zip` SHA-256: `7e56585f764fda18be85a9ba8ae45921e0fe62fef2aca53b2ea89918e47d6ba6`; 72 entries, no unsafe paths, and includes writable remount, `CALSTATUS`, and verified writes.

### Physical calibration evidence

After stage26 was installed, the board reported:

```text
OK|CALSTATUS|revision=pending|count=6|profiles=desktop:32.5;login-or-dc:25.0;character-dashboard:31.0;entering-game-loading:5.0;game:26.0;targeted:20.0|last_error=none
```

The latest `guard-calibration.json` copied from the board has SHA-256 `4123a643595ffd951af3c58aa076bc5e507958b730b1cba4f274ad3c140ec7ef` and contains six physically updated profiles:

- `desktop=32.5`, tolerance `3.75`
- `login-or-dc=0.0`, tolerance `5.0`
- `character-dashboard=11.666664`, tolerance `5.0`
- `entering-game-loading=35.0`, tolerance approximately `5.0`
- `game=22.5`, tolerance approximately `5.0`
- `targeted=20.83333`, tolerance `3.75`
- `stable_ms=750` for all profiles; revision remains `pending`.

This board file is the authoritative evidence that physical persistence for all six profiles is working. The export/default JSON must not overwrite it.

### Separate unresolved Windows Sync error

The current Status screen still shows:

```text
WriteFile failed: PermissionError(13, "The device does not recognize the command.", None, 22)
```

This is a Windows-side Sync/write-path failure, not evidence that Pico-side physical persistence failed. `pending` means the board's calibration is stored but has not yet been reconciled with the application revision. Guard remains OFF; operational routes, HID, and actuators remain blocked.

## Exact next action

1. Preserve the board's current `guard-calibration.json`, `guard-transition.json`, and `SHA256SUMS.txt`; do not overwrite them with export defaults.
2. Run `Guard / CALGET` and confirm `count=6` and the six persisted values.
3. Fix or bypass the Windows `Sync شش پروفایل` WriteFile path; treat the board JSON as source of truth until that path is proven.
4. Only after the revision mismatch is resolved should Guard ON be considered, with route/HID/actuator gates still separate.
5. The requested Status-tab move to the header/separate window remains a later UI task, after persistence and Sync are stable.
