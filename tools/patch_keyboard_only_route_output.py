#!/usr/bin/env python3
"""Keep keyboard-only Guard routes independent from ARM cursor synchronization."""
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

helper = '''_MOUSE_ROUTE_OPS = ("RMOUSE", "MOVETO")


def _route_requires_cursor_sync(name):
    """Return True only when a validated route contains a mouse movement."""
    with open("/" + name, "r") as fh:
        while True:
            raw = fh.readline()
            if not raw:
                return False
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            split = line.find("|")
            op = (line if split < 0 else line[:split]).upper()
            if op in _MOUSE_ROUTE_OPS:
                return True


'''

if "def _route_requires_cursor_sync(name):" not in s:
    anchor = "def _audible_loop(self):\n"
    if anchor not in s:
        raise SystemExit("missing audible-loop anchor")
    s = s.replace(anchor, helper + anchor, 1)

old_gate = '''                        if not _apply_pending_cursor(self, force=True):
                            _debug_event(self, "CURSOR", "sync-failed-before-route", persist=True)
                            raise RuntimeError("ARM cursor origin not acknowledged")
                        _debug_event(self, "CURSOR", "sync-ok-before-route", persist=True)
                        completed = self.route(decision)'''
new_gate = '''                        if _route_requires_cursor_sync(route_name):
                            if not _apply_pending_cursor(self, force=True):
                                _debug_event(self, "CURSOR", "sync-failed-before-route", persist=True)
                                raise RuntimeError("ARM cursor origin not acknowledged")
                            _debug_event(self, "CURSOR", "sync-ok-before-route", persist=True)
                        else:
                            _debug_event(self, "CURSOR", "not-required-keyboard-route", persist=True)
                        completed = self.route(decision)'''
if new_gate in s:
    pass
elif old_gate in s:
    s = s.replace(old_gate, new_gate, 1)
else:
    raise SystemExit("missing pre-route cursor gate anchor")

old_setup = '''    expected = getattr(owner, "debug_last_state", None)
    owner.light_poll_due = 0
    frames = []'''
new_setup = '''    expected = getattr(owner, "debug_last_state", None)
    owner.light_poll_due = 0
    route_uses_mouse = _route_requires_cursor_sync(name)
    frames = []'''
if new_setup in s:
    pass
elif old_setup in s:
    s = s.replace(old_setup, new_setup, 1)
else:
    raise SystemExit("missing light-route setup anchor")

old_screen = '''                owner.route_screen=(w,h)
                if not owner.arm.send("SETRES|%d,%d"%(w,h),3).startswith("OK|"): raise RuntimeError("ARM SETRES rejected")'''
new_screen = '''                owner.route_screen=(w,h)
                if route_uses_mouse:
                    if not owner.arm.send("SETRES|%d,%d"%(w,h),3).startswith("OK|"): raise RuntimeError("ARM SETRES rejected")'''
if new_screen in s:
    pass
elif old_screen in s:
    s = s.replace(old_screen, new_screen, 1)
else:
    raise SystemExit("missing route SCREEN/SETRES anchor")

required = (
    'def _route_requires_cursor_sync(name):',
    'if _route_requires_cursor_sync(route_name):',
    '"not-required-keyboard-route"',
    'route_uses_mouse = _route_requires_cursor_sync(name)',
    'if route_uses_mouse:',
)
missing = [token for token in required if token not in s]
if missing:
    raise SystemExit("keyboard-only cursor gate missing: " + ", ".join(missing))

p.write_text(s, encoding="utf-8", newline="\n")
print("patched keyboard-only route cursor gate:", p)
