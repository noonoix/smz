# Classroom Studio / SMC development rules

These rules apply before every build, release artifact, firmware bundle, commit, or PR update.

## 1. Mandatory pre-build review

Never start a new build immediately after editing code.

Before each build:

1. Identify the exact source commit and changed files.
2. Review the complete diff, not only the last edited file.
3. Trace generated and copied artifacts back to their canonical source files.
   In particular verify that `firmware/pico-light-guard-1.0.0/code.py` is the same file copied to the Windows output `combined-runtime/code.py` and then into the exported Pico bundle.
4. Check for stale generated copies, duplicate runtime directories, old build output, and wrong-branch files.
5. Verify that the requested behavior is represented in the actual artifact-producing path, not only in a test fixture or an unused source file.
6. Perform a contradiction scan: compare the user requirement, current implementation, tests, README/runtime contract, and generated artifact.
7. Record the review result before invoking `dotnet build`, packaging, or release creation.

If the review finds a stale source or an unresolved contradiction, stop and fix it before building.

## 2. Required validation gates

Run the lightest relevant checks first, then the complete project gates:

- Python syntax: `python3 -m py_compile` for every changed Pico/runtime Python file.
- .NET build: `dotnet build ams-shell/AMS.sln -c Release --no-restore` when restore is already valid.
- Project tests and contract tests, including portable Plan, Pico Guard, calibration/audio, and Windows TestRunner checks when applicable.
- Validate the exact exported inventory, SHA256 manifest, six optical profiles, route files, and `Resumable`.
- Inspect the final artifact itself; passing source tests alone is not sufficient.

If a test fails, read and classify the failure, fix it, and rerun the relevant gate. Do not report success from a partial or skipped build. Maximum three focused attempts; then report the blocker honestly.

## 3. Firmware and bundle safety

- Keep the canonical firmware source in `firmware/pico-light-guard-1.0.0/`.
- Do not maintain an untracked or silently divergent copy under `combined-runtime/` or `portable-runtime/`.
- If a generated/copy step is required, verify its SHA256 or exact content against the canonical source before packaging.
- The complete Pico bundle must contain all expected files and a manifest whose hashes match the payloads.
- Never copy a partial bundle to CIRCUITPY as if it were valid.
- Preserve `disable_concurrent_write_protection=True`; do not reintroduce write protection.
- Keep Guard fail-closed for invalid, incomplete, ambiguous, or stale calibration data.

## 4. Review checklist for physical-button behavior

For GP4/GP3 changes, verify both source and final `code.py`:

- A short GP4 press starts once on release.
- A long GP4 press enters calibration without also emitting the normal Start cue.
- GP4 advances to the next calibration position after a completed sample.
- GP3 starts sampling and the completed sample is saved once automatically.
- No button event can invoke the same tone or operation twice.
- Host `GUARD|ON` and physical GP4 must not double-start the same session.

## 5. Security and change hygiene

Before commit or PR update, scan changed files for:

- tokens, passwords, private keys, `.env` files, and credentials;
- accidental binaries or unrelated large artifacts;
- destructive commands, unsafe flashing, or write-protect changes;
- edits made on an archived or wrong base branch.

Do not commit secrets. Do not overwrite user calibration or macro data without an explicit migration/backup path.

## 6. Evidence-based reporting

Every completion report must state:

- exact commit and branch;
- review performed and important findings;
- tests/builds actually run and their result;
- skipped, queued, or failed checks;
- exact artifact path or download location, if available.

Never call a build successful while a required check is still queued, skipped, or failing. If the final artifact was not inspected, say so explicitly.

## 7. Clean-up and recovery

Use temporary directories for extraction and generated output. Do not delete user files silently. Before removing caches or logs, check their size and age; warn before deleting anything larger than 100 MB. Preserve a rollback copy before migrations or firmware changes.

## 8. Design and implementation discipline

Prefer one canonical source of truth. Keep export, import, runtime, tests, and documentation aligned. When a user reports behavior from a physical artifact, inspect that exact artifact before changing source code. Treat one passing test as evidence of a hypothesis, not proof of hardware correctness; require independent source/build/artifact confirmation.
