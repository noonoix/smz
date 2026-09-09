# 2026-09-09 - CI run #19 was red: release pins bumped to 0.9.64 (Pico bundle 0.9.64b)

## What broke

PR #13 ported the code64b Start/Stop teleport fix into the app and moved
`PicoFirmwareExporter.BundleVersion` to `0.9.64b`, but deliberately left the
release pins where they were (`Ams.UI.csproj` -> `0.9.60`, the `MainViewModel`
startup banner -> `v0.9.60`). "Bump the versions during the release step" was
the wrong call: TestRunner pins the whole version family together, so run #19
failed with

```
=== Results: 680 passed, 12 failed ===
```

and never reached the packaging step, which is why no `ci-19` release exists.
All 12 failures were version-pin guards (issue #14):

```
FAIL: v0.9.45 .. v0.9.50->51: app version, banner and Pico bundle version match   (6)
FAIL: v0.9.52 / v0.9.55 (x2): version pins for this release (csproj + banner + bundle)
FAIL: v0.9.56: BundleVersion is 0.9.60
FAIL: v0.9.60: version pins (firmware bundle, csproj, app banner)
FAIL: v0.9.60: exported code.py is fully baked with the fixed control contract
```

The last one looks like a template regression but is not: it only failed on
`code60.Contains("pico-light 0.9.60")`, i.e. the exported banner string, which
is generated from `BundleVersion`.

## Why the pins are hard to move

`tests/TestRunner.cs` (3,625 lines) has **no** version constant. The release
version is hardcoded 77 times:

| pattern | count |
| --- | --- |
| `csp.Contains("<Version>0.9.60</Version>")` | 23 |
| `vm.Contains("Classroom Studio v0.9.60")` | ~15 |
| `exp.Contains("BundleVersion = \"0.9.60\"")` | ~10 |
| `PicoFirmwareExporter.BundleVersion == "0.9.60"` | 2 |
| assertion labels (`"csproj version is 0.9.60"`, ...) | 4 |
| `code60.Contains("pico-light 0.9.60")` | 1 |

On top of that there is a **meta guard** (v0.9.58, TestRunner.cs ~3478-3492)
that reads TestRunner's own source, regex-extracts `0\.9\.(\d+)` from every
line containing `<Version>0.9.`, `Classroom Studio v0.9.` or `BundleVersion`,
skips the `v0.9.NN:` label form, and asserts that every remaining pin equals
`var curMinor = <N>;`. So a partial bump can never be green - every pin plus
`curMinor` has to move in the same commit.

## The version scheme

* app (`Ams.UI.csproj` `<Version>`, `MainViewModel` banner) -> **0.9.64**
* Pico firmware bundle (`PicoFirmwareExporter.BundleVersion`, exported
  `code.py` banner, `PONG`) -> **0.9.64b**
* `curMinor` -> **64**

`<Version>0.9.64b</Version>` is not valid for MSBuild, so the app pin drops the
suffix. The bundle keeps `b` on purpose: the exported `code.py` must stay
byte-identical to the golden `firmware/code64b/code64b.py`, whose banner is
`pico-light 0.9.64b`. The meta guard only reads the digits, so `0.9.64b`
counts as 64 and the family stays consistent.

## How it was applied

`tools/patch_version_pins_0964.py` - idempotent, anchored, fails loudly:
every edit declares a minimum occurrence count, and after patching it asserts
the exporter still says `BundleVersion = "0.9.64b"`, that the set of pins found
by the meta-guard logic is exactly `{64}`, and that csproj + banner are on
`0.9.64`. Re-running it is a no-op.

## Verification (Windows, before touching main)

`build.yml` only runs on pushes to `main`, so the bump was proven on a
throwaway workflow on the fix branch that mirrored `build.yml` step by step and
committed its result to a small report file (the Actions log is not readable
from the tooling used here):

```
run=2
test_step=success
results==== Results: 692 passed, 0 failed ===
fail_count=0
```

### Trap worth remembering

The first verification attempt reported

```
=== Results: 688 passed, 2 failed ===
FAIL: v0.9.58d: send_path parses semicolon-delimited delays, not individual characters
FAIL: v0.9.60: bridge stdio is forced to UTF-8 with an ASCII-safe emit fallback
```

Both read `bridge.py`, which this change never touches. The cause was the
missing `Remove-Item -Recurse -Force tests/bin, tests/obj` step: the repo
carries committed test output, including a stale
`tests/bin/Release/net8.0-windows/bridge/bridge.py`, and an incremental build
kept it. `build.yml` wipes those directories for exactly this reason - any
workflow that runs TestRunner must do the same, or it will report failures that
do not exist.

## Reproduce from scratch

```
python tools/patch-v0.9.61.py .
python tools/make_fw_template_0.9.64b.py .
python tools/patch_version_pins_0964.py
python -m py_compile ams-shell/bridge/bridge.py
python tools/test_bridge_pico.py
python firmware/code64b/code64b_check.py firmware/code64b/code64b.py
```

## Files changed by the bump

* `ams-shell/src/Ams.UI/Ams.UI.csproj` - `<Version>0.9.64</Version>`
* `ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs` - banner `Classroom Studio v0.9.64`
* `tests/TestRunner.cs` - 77 pins + `curMinor = 64`
* `tools/patch_version_pins_0964.py` - the patcher itself (kept next to the code it patches)

The app version and the firmware bundle version now move together, so the first
release built from this commit is also the first app whose
"File -> Export Pico Firmware" writes the healthy 0.9.64b firmware.
