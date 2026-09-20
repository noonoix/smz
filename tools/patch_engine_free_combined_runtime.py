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
    elif new_route not in s:
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
else:
    raise SystemExit("expected code.py or combined_guard_runtime.py")

p.write_text(s, encoding="utf-8", newline="\n")
print("patched engine-free Combined Guard:", p)
