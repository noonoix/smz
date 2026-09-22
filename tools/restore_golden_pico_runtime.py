#!/usr/bin/env python3
"""Restore the reviewed Golden Pico entry point after legacy build patchers.

The Windows application still runs historical code patchers for older firmware
fixtures. They are intentionally allowed to run for compatibility tests, but
must never mutate the marker-bearing Golden Pico source used by the combined
export. This final step makes the artifact byte-identical to that source.
"""
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: restore_golden_pico_runtime.py OUTPUT SOURCE")
out = Path(sys.argv[1])
source = Path(sys.argv[2])
out_text = out.read_text(encoding="utf-8")
source_text = source.read_text(encoding="utf-8")
marker = "# GOLDEN_PICO_RUNTIME_52_RPKG"
if marker in out_text and marker in source_text:
    shutil.copyfile(source, out)
    print("Golden Pico runtime restored", out)
else:
    print("legacy Pico runtime preserved", out)
