# PLAN2 split runtime — hardware and CI checkpoint

## Why the runtime was split

The canonical PLAN|2 engine is 50,174 bytes. Importing it directly on the RP2040 under CircuitPython 10.3.0 failed with:

```text
memory allocation failed, allocating 3112 bytes
```

The fix preserves the canonical source and all opcodes. `tools/split_plan_engine.py` deterministically generates three modules and lazy-loads motion/typing only when needed.

## Generated modules

| File | Bytes | SHA-256 |
|---|---:|---|
| `plan_engine.py` | 24,994 | `c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac` |
| `plan_motion.py` | 14,028 | `9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8` |
| `plan_typing.py` | 3,967 | `1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5` |

Canonical engine SHA-256: `b94b4e8ba3647851814e0a7ea6a1ceb9d92c033a3ad8cc7058a0143853ed3674`.

## Hardware checkpoint

Firmware banner: `pico-light 0.9.64f-plan2h4`.

Captured on 2026-09-11:

```text
plan: loaded 7 ops
plan: rmouse -> (1286,234) 175 pts
```

The test plan executes TYPE before RMOUSE, so reaching RMOUSE proves the core and typing modules loaded and completed far enough for the motion module to load. No MemoryError, run error, or ACK watchdog reset appeared in the 60-second log.

## Exporter integration

`Export Pico Plan` now publishes these runtime files together with root/child plans and the README:

- `plan_engine.py`
- `plan_motion.py`
- `plan_typing.py`

All files participate in the existing atomic staging/publish/rollback transaction. C# tests verify all three generated files are present, byte-identical to their embedded copies, and restored on forced publication failure.

## Gates

- split differential parity: `18 passed, 0 failed`
- original Python suites: `103 passed, 0 failed`
- Windows app build: `0 errors`
- TestRunner: `752 passed, 0 failed`
- sensitive-file guard: passed

PR #26 remains Draft until the final h4 PONG and observed one-shot typing/motion confirmation are recorded. Version bump remains a separate PR.
