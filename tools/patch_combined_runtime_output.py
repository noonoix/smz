#!/usr/bin/env python3
"""Idempotently patch the Combined Guard runtime packaged by Classroom Studio."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacements = {
    'raise GuardBundleError("unvalidated route")': 'raise runtime.GuardBundleError("unvalidated route")',
    '_run_light_route(PlanContext(self), route)': '_run_light_route(runtime.PlanContext(self), route)',
    'runtime.plan_engine.run_plan(route, PlanContext(self))': 'runtime.plan_engine.run_plan(route, runtime.PlanContext(self))',
    '_LIGHT_ROUTE_COMMANDS = {"SCREEN", "SPEED", "BEEP", "DELAY"}': '_LIGHT_ROUTE_COMMANDS = {"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY"}',
    '    for command, args in commands:\n        if command == "SCREEN":': '    for command, args in commands:\n        if command == "PLAN":\n            if args != "2":\n                raise ValueError("unsupported PLAN version")\n            continue\n        if command == "SCREEN":',
    '    if persist or any(kind.startswith(prefix) for prefix in _DEBUG_PERSIST_EVENTS):\n        _debug_persist(self)': '    if kind in ("BOOT", "FAIL"):\n        _debug_persist(self)',
}
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
    elif new not in text:
        raise SystemExit(f"runtime patch anchor missing: {old[:80]}")

safe_persist = '''def _debug_persist(self):
    # Live tracing belongs to GuardTraceCollector. Never remount or rewrite
    # CIRCUITPY on GP4/STATE/ROUTE events; keep only BOOT/FAIL breadcrumbs in NVM.
    try:
        payload = _debug_trim(_debug_nvm_read() + "".join(self.debug_events))
        ok = _debug_nvm_write(payload)
        if ok:
            self.debug_events = []
        return ok
    except Exception:
        return False

'''
if "Live tracing belongs to GuardTraceCollector" not in text:
    text, count = re.subn(r'def _debug_persist\(self\):\n.*?(?=def _debug_event\(self,)', safe_persist, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("runtime patch anchor missing: _debug_persist")

path.write_text(text, encoding="utf-8", newline="\n")
print(f"verified Combined Guard runtime patch: {path}")
