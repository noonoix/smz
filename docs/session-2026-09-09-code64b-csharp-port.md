# code64b app/C# port — 2026-09-09

## Goal

Persist the proven code64b Stop/Start cursor fix in the Classroom Studio app line, not only in the standalone Pico zip.

## Changes

- `PicoFirmwareExporter.CodeTemplate` is regenerated from `firmware/code64b/code64b.py` while preserving all seven live exporter placeholders.
- `PicoFirmwareExporter.BundleVersion` becomes `0.9.64b`.
- `RunEngine` syncs the board's tracked absolute cursor to the real Windows cursor immediately before click, wheel, button-down, and button-up actions.
- `bridge.py` gains stale-reply filtering/draining, payload-sized KTEXT timeout, local acknowledgement for fire-and-forget MMOVE, path thinning at hardware cadence, one retry for UART `ERR|UNKNOWN`, and interpolated `abs,2` path points.
- Reproduction tools are committed under `tools/` and are idempotent.

## Why the Stop/Start teleport happened

The arm firmware includes its tracked absolute X/Y position in mouse button reports. The old routine GP4 Start/Stop path sent three unconditional `MUP` reports even when no button was held. Those reports carried stale tracked axes, producing a 964–1216 px snap in five of fourteen recorded toggles. code64b tracks held buttons and releases only those buttons on routine Start/Stop; abnormal HALT/BYE/abort/error and a GP4 hold of at least one second retain the full three-button safety release.

## Verification gates

- Source blobs were fetched from main commit `1677e5bd800ad52c37e8cef7e0e021d2feb90378` and matched their GitHub blob SHA before patching.
- Simulated `BuildCodePy` output equals the golden `code64b.py` byte-for-byte.
- Exported firmware sha256: `124eae5296d826162abc5261ed5f2ef869e71754fc805c9777002ad19ba6cc6e`.
- `code64b_check.py`: 34/34 passed.
- `test_bridge_pico.py`: 16/16 passed.
- Patched `bridge.py`: `py_compile` passed.
- Full .NET/WPF build is delegated to the repository's Windows CI because the local sandbox has no `dotnet` runtime.

## Reproduce

```bash
python tools/patch-v0.9.61.py .
python tools/make_fw_template_0.9.64b.py .
python -m py_compile ams-shell/bridge/bridge.py
python tools/test_bridge_pico.py
python firmware/code64b/code64b_check.py firmware/code64b/code64b.py
```

Both patch commands are safe to re-run. The generator verifies an already-patched exporter without rewriting it.

## Release note

The startup banner in the 98 KB `MainViewModel.cs` remains unchanged in this source-port commit. The firmware identifies itself as `pico-light 0.9.64b`; the app assembly/version pin should be bumped only after Windows CI succeeds and the release number is chosen.
