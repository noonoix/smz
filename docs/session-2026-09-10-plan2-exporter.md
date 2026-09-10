# PLAN|2 exporter integration checkpoint — 2026-09-10

## Scope
Continue the verified `0.9.66 / PLAN|2` line on `feat/portable-plan2-app-0966` without modifying `main`.

## Completed
1. Recovered runtime/compiler/tests/fixtures were transferred to the clean feature branch and matched the uploaded v3.1 artifact byte-for-byte.
2. Pinned source hashes:
   - `portable/plan3/CIRCUITPY/plan_engine.py`: `b94b4e8ba3647851814e0a7ea6a1ceb9d92c033a3ad8cc7058a0143853ed3674`
   - `portable/plan3/sim/sim_plan3.py`: `edbb1439d5eb1ae8df96921cccc6e580b924360e8fec4eb39e734335ee2ac76f`
   - `portable/plan3/tools/winr.py`: `5aaddc4125c3c42dcb521f057c632338a9c26baa38b4b73305e0979e207a6d52`
   - `portable/plan3/sim/sim_plan2.py`: `481014a11f085820ad9a4bc259d4bd592f1e325f663d80b8585eb7a4dd891cc8`
3. Dedicated PLAN2 CI is green in both push and pull-request runs: `hashes`, `compile`, `sim2`, `sim3`, `compiler`, `golden`.
4. Deterministic results: `21/0 + 42/0 + 40/0 = 103 passed / 0 failed`; both golden plans validate.
5. GitHub Secret Scanning could not run because GitHub Advanced Security is not enabled for the repository. A targeted local preflight found no real credential; only deliberate test/document literals.
6. C# wiring stage started on commit `6abafc5304f4ae5c4bdea57b9aa0b4b05d55cc16`:
   - `PlanFormatVersion = 2`, output header `PLAN|2`, engine line `0.9.66`.
   - `tools/make_plan_exporter.py` now embeds `portable/plan3/CIRCUITPY/plan_engine.py` and enforces the pinned SHA-256 plus round-trip byte identity.
   - Generated `PlanExporter.cs` embeds the recovered engine.
   - Bundle publication (`plan.txt`, `plan_engine.py`, `README-PLAN.md`) stages all files before touching destinations and rolls back on failure.
7. PR #26 and Issue #25 were updated with the checkpoint and Secret Scanning limitation.

## Current branch
- Branch: `feat/portable-plan2-app-0966`
- Base: `main @ f9f819ba7a8a183f2c7f9040c039e7f502abbe26`
- Latest validation trigger at checkpoint: `71f1a59953e7d098adc863f8231e1ffeb10278d3`
- PR: https://github.com/pedrampedi81-dotcom/smc/pull/26 (Draft)
- Issue: https://github.com/pedrampedi81-dotcom/smc/issues/25

## Next execution order
1. Run a Windows branch build/TestRunner gate before expanding parity.
2. Upgrade the C# validator and emitters for `IFSND`, `IFLUX`, `ELSE`, `ENDIF`, `KEY`, `KDOWN`, `KUP`, `WHEEL`, `LABEL`, `GOTO`, `RAW`, `RPKG`, `PGROUP`, `INCLUDE`, and `BEEP`.
3. Add recursive include compilation with depth cap 4, cycle/missing-child blocking, and atomic publication of every child plan.
4. Port the reference compiler's deterministic and negative parity cases into TestRunner; unsupported/unknown steps must always block and never be skipped.
5. Run full Windows CI and require `0 failed` before requesting hardware validation.
6. Preserve the accepted hardware baseline: Pico transport `0.9.64f`, Pro Micro `2.5`, and zero `BADMOVE`, `PARTIAL WRITE`, `NO-DROP`, `CKSUM`, `NOFRAME`, or unintended excursions.
7. Only after hardware acceptance, prepare the version bump to `0.9.66` in a separate PR.

## Non-negotiable guards
- No direct changes to `main`.
- No selective merge.
- No real key files, personalized HEX, flash backups, or EEPROM backups in Git.
- No publish with a failing test.
- `findImage` and clipboard/secret typing remain explicit blocking errors.
