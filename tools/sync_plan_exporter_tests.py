#!/usr/bin/env python3
"""Replace the committed Step 59 block with the PLAN|2 include, deterministically."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
runner_path = root / "tests" / "TestRunner.cs"
inc_path = root / "tools" / "plan_exporter_test_step.cs.inc"
runner = runner_path.read_text(encoding="utf-8")
inc = inc_path.read_text(encoding="utf-8")

old = 'PlanExporter.PlanFormatVersion == 1 && PlanExporter.EngineVersion == "0.9.66"'
new = 'PlanExporter.PlanFormatVersion == 2 && PlanExporter.EngineVersion == "0.9.66"'
if old in inc:
    inc = inc.replace(old, new)
    inc_path.write_text(inc, encoding="utf-8", newline="\n")
if new not in inc:
    raise SystemExit("PLAN|2 version assertion is missing from the Step 59 include")

marker = "Step 59: v0.9.65 plan exporter"
pos = runner.find(marker)
if pos < 0:
    raise SystemExit("Step 59 marker not found in tests/TestRunner.cs")
# Start at the first stable include sentinel in the repeated preface region. Older
# CI runs started at the title line and could leave one preface behind each time.
sentinel = "        // PLAN2_PARITY_TESTS\n"
start = runner.rfind(sentinel, 0, pos)
if start < 0:
    raise SystemExit("Step 59 sentinel not found before marker")
while True:
    previous = runner.rfind(sentinel, 0, start)
    if previous < 0:
        break
    between = runner[previous + len(sentinel):start]
    if marker not in between and between.strip() not in {
        'Console.WriteLine();',
        '// ── Step 59: v0.9.65 — portable plan exporter (PLAN|2 gen-1 contract, firmware 0.9.64b) ──\n        Console.WriteLine();',
    }:
        break
    start = previous
results = '        Console.WriteLine($"=== Results: {passed} passed, {failed} failed ===");'
end = runner.find(results, pos)
if end < 0:
    raise SystemExit("Results anchor not found after Step 59")
updated = runner[:start] + inc.rstrip() + "\n" + runner[end:]
if updated.count(marker) != 1 or updated.count(results) != 1:
    raise SystemExit("postcondition failed while synchronizing Step 59")
runner_path.write_text(updated, encoding="utf-8", newline="\n")
print("SYNC OK: Step 59 now comes from tools/plan_exporter_test_step.cs.inc")
