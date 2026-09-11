#!/usr/bin/env python3
"""v0.9.67 auto-cycle layer for tools/plan_gen.py.

The existing compiler remains the single source for action lowering. This layer
adds root-only RUNFOR/AUTORESUME directives and validates the final text with the
cycle-aware parser. INCLUDE outputs remain byte-compatible and inherit root state.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_HERE)
for path in (_HERE, os.path.join(_BASE, "CIRCUITPY")):
    if path not in sys.path:
        sys.path.insert(0, path)

import cycle_export
import plan_cycle
import plan_gen


def inject_root_policy(text, settings):
    lines = text.splitlines()
    if not lines or not lines[0].startswith("PLAN|"):
        raise ValueError("generated root plan has no PLAN header")
    directives = cycle_export.cycle_lines(settings, root=True)
    out = "\n".join([lines[0]] + directives + lines[1:]) + "\n"
    # Dogfood the exact parser used by the Pico adapter.
    plan_cycle.parse_cycle_plan(out)
    return out


def build(source_path, opts):
    files, gen, child_gens = plan_gen.build(source_path, opts)
    root_name = opts["out_name"]
    if root_name not in files:
        raise ValueError("base compiler did not return root output '%s'" % root_name)
    files[root_name] = inject_root_policy(files[root_name], opts["settings"])
    # Child plans must never create independent timers or resume markers.
    for name, text in files.items():
        if name == root_name:
            continue
        if "\nRUNFOR|" in text or "\nAUTORESUME|" in text:
            raise ValueError("include '%s' contains a root-only cycle directive" % name)
    return files, gen, child_gens
