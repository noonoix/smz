# v0.9.66 — PLAN|2 app integration

Status: started on `feat/portable-plan2-app-0966` from `main` @ `f0865c22`.
Tracking: issue #25.

## Baseline that must not regress

- App/release baseline: `0.9.65` / `ci-25` / 744 passed, 0 failed.
- Pico transport and portable baseline: `pico-light 0.9.64f`.
- Pro Micro arm baseline: firmware `2.5`.
- Preserve strict framing, checksum, back-pressure, short-write handling and `BADMOVE` guard behavior.
- Do not bump the app version until the implementation PR is green and hardware acceptance passes.

## Repository audit — 2026-09-10

### Shipped app path

`ams-shell/src/Ams.UI/Services/PlanExporter.cs` is generated from
`tools/PlanExporter.cs.tpl`. It deliberately targets `PLAN|1`, embeds the gen-1
engine from `firmware/code64b/plan_engine.py`, compiles 8 of the 23 app actions,
and blocks the other 15 before writing any file.

The screenshot case (`waitForSound` with `insertIfElse`) is therefore an expected
`PLAN|1` block, not a parser failure.

### Parked complete compiler

`portable/plan3/tools/plan_gen.py` already defines the intended `PLAN|2` compiler
contract and its golden/negative/e2e suite lives in
`portable/plan3/sim/test_plan_gen.py`.

The compiler covers the expanded opcode set, including:

- `MOVETO`, `WHEEL`, `KEY`, `KDOWN`, `KUP`
- `WSND`, `TRGSND`, `IFSND`, `IFLUX`, `ELSE`, `ENDIF`
- `LABEL`, `GOTO`, `RAW`
- `RPKG`, `PKGITEM`, `ENDPKG`
- `PGROUP`, `PARITEM`, `ENDPAR`
- `INCLUDE`

`findImage`, clipboard/secret typing and other genuinely non-portable modes stay
blocking errors. Nothing unsupported may be silently skipped.

### First blocking gap found

The checked-in `portable/plan3` tree contains the compiler, fixtures and tests,
but the source-of-truth runtime modules imported by them are not present at the
expected paths:

- `portable/plan3/CIRCUITPY/plan_engine.py`
- `portable/plan3/tools/winr.py`

The current CI workflow also does not run the `portable/plan3` suite. Therefore
copying the Python compiler logic into C# immediately would create two drifting
implementations without a reproducible engine gate.

## Implementation order

1. Restore the byte-reviewed `PLAN|2` engine and `winr.py` helper under
   `portable/plan3`, then run the existing golden/negative/e2e suite in CI.
2. Generate the C# exporter from one pinned contract rather than hand-maintaining
   a second opcode implementation.
3. Embed/export the same verified `PLAN|2` engine beside `plan.txt`.
4. Add TestRunner parity cases for all portable actions and blocking modes.
5. Confirm the app writes no partial bundle on any validation error.
6. Build and run the full suite (`0 failed`).
7. Hardware acceptance on the existing `0.9.64f` + arm `2.5` link baseline.
8. Only then prepare the separate `0.9.66` version/release PR.

## Acceptance gates

- Generated main and included plans start with `PLAN|2` and parse with the exact
  engine that the app exports.
- Every portable action has deterministic coverage.
- Unsupported modes fail before the first file write and identify the offending
  step number/type/name.
- Existing `PLAN|1` behavior remains available until the `PLAN|2` bundle passes
  CI and hardware acceptance.
- Full TestRunner result is `0 failed`.
- Hardware run has zero unintended excursions and no checksum/framing/drop or
  partial-write regression.
