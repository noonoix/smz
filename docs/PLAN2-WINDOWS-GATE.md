# PLAN2 Windows gate report

- migration: success
- split runtime: failure
- bridge: skipped
- app build: skipped
- TestRunner: skipped

- result: 

## Migration tail
```
PLAN2 parity migration already applied
PLAN2 parity tests already applied
PLAN2 recursive-bundle migration already applied
PLAN2 recursive-bundle tests already applied
PLAN2 split-runtime template migration applied
PLAN2 split-runtime C# tests applied
plan_engine.py 24994 c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac
plan_motion.py 14028 9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8
plan_typing.py 3967 1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5
total 42989
wrote ams-shell\src\Ams.UI\Services\PlanExporter.cs (89914 chars)
plan_engine.py 24994 c12f2f9c32ddc8648b32cd103b3158abe39c2b05beae914e6a9ce685819fc5ac
plan_motion.py 14028 9a088d2e9d8c032ca39faef119f580852534d844c52f79188501d845103655f8
plan_typing.py 3967 1a0ea9e79ece0aeee85530e2ac583c75067298b5f29f21383152fea160a235c5
round trip: all three split modules byte-identical
MAKE OK
SYNC OK: Step 59 now comes from tools/plan_exporter_test_step.cs.inc
```

## Split-runtime tail
```
[Errno 22] Invalid argument: 'portable/plan3/CIRCUITPY-SPLIT/*.py'
```

## App build tail
```
```

## Test tail
```
```
