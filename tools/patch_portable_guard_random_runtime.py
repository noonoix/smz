#!/usr/bin/env python3
"""Include the lazy Random Package executor in Combined Guard exports."""
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

old_runtime = '''        "plan_engine.py", "live_light_guard.py", "guard_transition.py", "guard_calibration_protocol.py", "error_policy.py", "combined_guard_runtime.py",'''
new_runtime = '''        "plan_engine.py", "live_light_guard.py", "guard_transition.py", "guard_calibration_protocol.py", "error_policy.py", "combined_guard_runtime.py", "random_package_runtime.py",'''
if old_runtime in s:
    s = s.replace(old_runtime, new_runtime, 1)
elif new_runtime not in s:
    raise SystemExit("PortableGuardBundle RuntimeFiles anchor missing")

old_inventory = '''        "plan.txt", "plan_engine.py", "README-FLASH.md", "resumable_steps.txt", "SHA256SUMS.txt",'''
new_inventory = '''        "plan.txt", "plan_engine.py", "random_package_runtime.py", "README-FLASH.md", "resumable_steps.txt", "SHA256SUMS.txt",'''
if old_inventory in s:
    s = s.replace(old_inventory, new_inventory, 1)
elif new_inventory not in s:
    raise SystemExit("PortableGuardBundle inventory anchor missing")

s = s.replace("complete 21-file staging bundle", "complete 22-file staging bundle")
s = s.replace("exact 21-file inventory", "exact 22-file inventory")
s = s.replace("hashes for the other 20 files", "hashes for the other 21 files")

if s.count('"random_package_runtime.py"') != 2:
    raise SystemExit("Random Package runtime must appear exactly in runtime and inventory arrays")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched PortableGuardBundle Random Package inventory:", p)
