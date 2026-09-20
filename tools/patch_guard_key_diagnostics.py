#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old_key = '''    pressed = 0
    try:
        for code in codes:
            owner.keyboard.press(code); pressed += 1
        if hold and not _light_sleep(owner, hold, expected_state): return False
        return _light_gate(owner, expected_state)
    finally:
        while pressed:
            pressed -= 1
            owner.keyboard.release(codes[pressed])
'''
previous_key = '''    pressed = 0
    try:
        owner.emit("EVT|DEBUG|STEP/KEY press-start")
        for code in codes:
            owner.keyboard.press(code); pressed += 1
        owner.emit("EVT|DEBUG|STEP/KEY pressed")
        if hold and not _light_sleep(owner, hold, expected_state): return False
        owner.emit("EVT|DEBUG|STEP/KEY release-start")
        while pressed:
            pressed -= 1
            owner.keyboard.release(codes[pressed])
        owner.emit("EVT|DEBUG|STEP/KEY released")
        return _light_gate(owner, expected_state)
    finally:
        while pressed:
            pressed -= 1
            try:
                owner.keyboard.release(codes[pressed])
            except Exception as cleanup:
                owner.emit("EVT|DEBUG|STEP/KEY cleanup-failed " + type(cleanup).__name__)
'''
new_key = '''    pressed = 0
    try:
        owner.emit("EVT|DEBUG|STEP/KEY press-start")
        for index in range(len(codes)):
            owner.emit("EVT|DEBUG|STEP/KEY press-index=%d code=%d" % (index, codes[index]))
            owner.keyboard.press(codes[index]); pressed += 1
            owner.emit("EVT|DEBUG|STEP/KEY press-ok=%d" % index)
        owner.emit("EVT|DEBUG|STEP/KEY pressed")
        if hold and not _light_sleep(owner, hold, expected_state): return False
        owner.emit("EVT|DEBUG|STEP/KEY release-start")
        while pressed:
            pressed -= 1
            owner.emit("EVT|DEBUG|STEP/KEY release-index=%d code=%d" % (pressed, codes[pressed]))
            owner.keyboard.release(codes[pressed])
        owner.emit("EVT|DEBUG|STEP/KEY released")
        return _light_gate(owner, expected_state)
    finally:
        while pressed:
            pressed -= 1
            try:
                owner.keyboard.release(codes[pressed])
            except Exception as cleanup:
                owner.emit("EVT|DEBUG|STEP/KEY cleanup-failed " + type(cleanup).__name__)
'''
if previous_key in s:
    s = s.replace(previous_key, new_key, 1)
elif old_key in s:
    s = s.replace(old_key, new_key, 1)
elif new_key not in s:
    raise SystemExit("missing KEY diagnostic anchor")
old_route = '''    try:
        _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key.
        self.keyboard.release_all()
        self.arm.flush()
'''
new_route = '''    primary = None
    try:
        _run_light_route(self, name)
    except Exception as exc:
        primary = exc
        raise
    finally:
        # Cleanup failures are reported, but never replace the primary route error.
        try:
            self.keyboard.release_all()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/keyboard " + type(cleanup).__name__)
            if primary is None:
                raise
        try:
            self.arm.flush()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/arm " + type(cleanup).__name__)
            if primary is None:
                raise
'''
if old_route in s:
    s = s.replace(old_route, new_route, 1)
elif new_route not in s:
    raise SystemExit("missing route cleanup anchor")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched", p)
