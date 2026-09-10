# PLAN2 Windows gate report

- generation: failure
- bridge compile: success
- bridge test: success
- restore: success
- app build: success
- TestRunner build: success
- TestRunner run: failure

## Build tail
```
  Determining projects to restore...
  Restored D:\a\smc\smc\tests\TestRunner.csproj (in 825 ms).
  1 of 2 projects are up-to-date for restore.
  Ams.UI -> D:\a\smc\smc\ams-shell\src\Ams.UI\bin\Release\net8.0-windows\ClassroomStudio.dll
D:\a\smc\smc\tests\TestRunner.cs(562,27): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\tests\TestRunner.csproj]
  TestRunner -> D:\a\smc\smc\tests\bin\Release\net8.0-windows\TestRunner.dll

Build succeeded.

D:\a\smc\smc\tests\TestRunner.cs(562,27): warning CS8602: Dereference of a possibly null reference. [D:\a\smc\smc\tests\TestRunner.csproj]
    1 Warning(s)
    0 Error(s)

Time Elapsed 00:00:13.55
```
## Test failures/results
```
SKIP: daroon1.amk not present on this machine — daroon import test skipped (CI-safe)
SKIP: daroon1.amk not present on this machine — PNG extraction test skipped (CI-safe)
SKIP: daroon1.amk not present on this machine — native image extraction test skipped (CI-safe)
FAIL: v0.9.65: plan header is PLAN|1 with SCREEN and SPEED from settings
FAIL: v0.9.65: randomMousePosition compiles on PLAN|1
FAIL: v0.9.65: mouseMove compiles on PLAN|1
FAIL: v0.9.65: mouseClick compiles on PLAN|1
FAIL: v0.9.65: delay compiles on PLAN|1
FAIL: v0.9.65: waitForLight compiles on PLAN|1
FAIL: v0.9.65: comment compiles on PLAN|1
FAIL: v0.9.65: the embedded plan engine is byte-identical to firmware/code64b/plan_engine.py
FAIL: v0.9.65: the plan exporter targets the current firmware bundle line (PLAN|1)
FAIL: v0.9.65: the written bundle carries the plan and the real engine
=== Results: 750 passed, 10 failed ===
```
