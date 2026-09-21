#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

if p.name == "combined_guard_runtime.py":
    # Stop is an emergency path. Waiting for a HALT acknowledgement while the
    # arm is in a human-mouse wait can delay or lose the button-up frames.
    old_abort = '''    def abort(self):
        try: self.send("HALT", 1.5)
        except Exception: pass
        self.release(True)
'''
    new_abort = '''    def abort(self):
        # Nonblocking fail-safe stop: queue HALT and explicit MUP frames first,
        # then drain replies. Do not wait for an acknowledgement before sending
        # the button-up frames; an in-flight HMOVE/MCLICK may be aborting.
        for line in ("HALT", "MUP|left", "MUP|right", "MUP|middle"):
            try:
                self.write(line)
                time.sleep(.003)
            except Exception:
                pass
        end = time.monotonic() + .35
        while time.monotonic() < end:
            self.pump()
            time.sleep(.002)
        self.held.clear(); self.pending = 0
'''
    if old_abort in s:
        s = s.replace(old_abort, new_abort, 1)
    elif new_abort not in s:
        raise SystemExit("missing Arm.abort anchor")

    # A route may end while MDOWN/MCLICK is active. flush() alone drains UART;
    # it does not release the HID buttons held by the Pro Micro.
    old_route = "        plan_engine.run_plan(self.routes[name], PlanContext(self)); self.arm.flush()\n"
    new_route = '''        try:
            plan_engine.run_plan(self.routes[name], PlanContext(self))
        finally:
            # Fail-safe route cleanup: never leave a physical mouse button held
            # when a route completes, aborts, or raises.
            self.arm.release(True)
            self.arm.flush()
'''
    if old_route in s:
        s = s.replace(old_route, new_route, 1)
    else:
        if not ("self.arm.prepare_route()" in s and
                "plan_engine.run_plan(" in s and
                "self.arm.release(True)" in s):
            raise SystemExit("missing route cleanup anchor")

    old = "import plan_engine\n"
    new = "# Combined Guard routes are executed only by the bounded streaming runner.\n"
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("missing combined runtime plan_engine import anchor")
    s = s.replace("raise plan_engine.PlanAbort()", "raise RuntimeError(\"route aborted\")")
    if "import plan_engine" in s:
        raise SystemExit("Combined runtime still imports plan_engine")
elif p.name == "code.py":
    start = s.find("class _DeferredPlanEngine:")
    end_marker = 'sys.modules["plan_engine"] = _DeferredPlanEngine()\n'
    if start >= 0:
        end = s.find(end_marker, start)
        if end < 0:
            raise SystemExit("missing deferred engine end anchor")
        end += len(end_marker)
        s = s[:start] + "# plan_engine is intentionally absent from Combined Guard.\n" + s[end:]
    elif "plan_engine is intentionally absent from Combined Guard" not in s:
        raise SystemExit("missing deferred engine anchor")
    s = s.replace("# shims, and defer the 57 KB plan engine until route execution.",
                  "# shims, and keep all Guard routes on the bounded streaming executor.")
    if "_DeferredPlanEngine" in s or 'sys.modules["plan_engine"]' in s:
        raise SystemExit("Deferred plan_engine proxy remains")

    # Every generated route uses the bounded streaming executor.  Before a
    # new route, cancel any in-flight ARM human-mouse operation and send MUP
    # frames.  Without this boundary the Pro Micro can retain stale move debt;
    # repeated routes then stop after fewer and fewer RMOUSE commands until a
    # power cycle resets the ARM.
    route_start = """    primary = None
    try:
"""
    route_start_fixed = """    primary = None
    try:
        self.arm.prepare_route()
"""
    simple_route_start = """    try:
        _run_light_route(self, name)
"""
    simple_route_start_fixed = """    try:
        self.arm.prepare_route()
        _run_light_route(self, name)
"""
    if route_start in s and route_start_fixed not in s:
        s = s.replace(route_start, route_start_fixed, 1)
    elif route_start_fixed not in s:
        # The checked-in firmware fixture uses the smaller route wrapper;
        # generated output uses the primary/except wrapper. Support both.
        if simple_route_start in s and simple_route_start_fixed not in s:
            s = s.replace(simple_route_start, simple_route_start_fixed, 1)
        elif simple_route_start_fixed not in s:
            raise SystemExit("missing streaming route start anchor")

    # The streaming runner is the active route path for the combined firmware.
    # It already releases the keyboard in its finally block, but previously
    # only flushed the UART. A route ending after MDOWN/MCLICK could therefore
    # leave the Pro Micro's left button physically held until Ctrl+Alt+Del.
    old_cleanup = '''        try:
            self.arm.flush()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/arm " + type(cleanup).__name__)
'''
    new_cleanup = '''        try:
            self.arm.release(True)
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/mouse " + type(cleanup).__name__)
        try:
            self.arm.flush()
        except Exception as cleanup:
            self.emit("EVT|DEBUG|CLEANUP/arm " + type(cleanup).__name__)
'''
    if old_cleanup in s:
        s = s.replace(old_cleanup, new_cleanup, 1)
    elif new_cleanup not in s:
        # The checked-in firmware fixture has a smaller diagnostic route block
        # than the packaged/generated code. Keep both source and build layouts
        # covered; this also makes the patch testable without a full .NET build.
        old_simple = '''    try:
        _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key.
        self.keyboard.release_all()
        self.arm.flush()
'''
        old_simple_prepared = '''    try:
        self.arm.prepare_route()
        _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key.
        self.keyboard.release_all()
        self.arm.flush()
'''
        new_simple = '''    try:
        self.arm.prepare_route()
        _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key
        # or mouse button.
        self.keyboard.release_all()
        try:
            self.arm.release(True)
        except Exception:
            pass
        self.arm.flush()
'''
        new_simple_prepared = '''    try:
        _run_light_route(self, name)
    finally:
        # A state transition, Stop or parser failure must never leave a held key
        # or mouse button.
        self.keyboard.release_all()
        try:
            self.arm.release(True)
        except Exception:
            pass
        self.arm.flush()
'''
        if old_simple in s:
            s = s.replace(old_simple, new_simple, 1)
        elif old_simple_prepared in s:
            s = s.replace(old_simple_prepared, new_simple, 1)
        elif new_simple not in s and new_simple_prepared not in s:
            raise SystemExit("missing streaming route cleanup anchor")
else:
    raise SystemExit("expected code.py or combined_guard_runtime.py")

p.write_text(s, encoding="utf-8", newline="\n")
print("patched engine-free Combined Guard:", p)
