from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "portable/plan3/CIRCUITPY/plan_engine.py"
text = ENGINE.read_text(encoding="utf-8")
marker = "# live-light-guard-v1"
if marker in text:
    print("live light guard already applied")
    raise SystemExit(0)

old = '        "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "WLIGHT",\n'
new = '        "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "WLIGHT", "STATELOOP",\n'
if old not in text:
    raise SystemExit("plan_engine: _OPS anchor not found")
text = text.replace(old, new, 1)

old = '        elif op == "WLIGHT":\n'
new = '''        elif op == "STATELOOP":
            # v4: the portable live light guard owns routing and returns only
            # when the keypad stops the run or the sensor becomes unsafe.
            _run_state_loop(prm, ctx, pos, pauses, inc)
        elif op == "WLIGHT":
'''
if old not in text:
    raise SystemExit("plan_engine: executor anchor not found")
text = text.replace(old, new, 1)

old = '        if _gate is not None and not _gate():\n            raise PlanAbort()\n'
new = '''        if _gate is not None and not _gate():
            raise PlanAbort()
        _live_guard = getattr(ctx, "_live_light_guard", None)
        if _live_guard is not None:
            # Safe handoff point: polling is performed before every operation;
            # a changed state aborts the current route before the next action.
            _live_guard.poll()
'''
if old not in text:
    raise SystemExit("plan_engine: gate anchor not found")
text = text.replace(old, new, 1)

old = '        elif op in ("WSND", "TRGSND", "IFSND", "IFLUX"):\n'
insert = '''        elif op == "STATELOOP":
            # Syntax: STATELOOP|poll=250|stable=750|hysteresis=20|timeout=1500|
            #         routes=id:lo:hi:file.txt,id2:lo:hi:file.txt
            vals = {}
            for kv in fields[1:]:
                if "=" not in kv:
                    raise ValueError("line %d: STATELOOP wants key=value" % line_no)
                k, v = kv.split("=", 1)
                vals[k.strip().lower()] = v.strip()
            try:
                prm["poll"] = max(25, int(vals.get("poll", "250")))
                prm["stable"] = max(0, int(vals.get("stable", "750")))
                prm["hysteresis"] = max(0, int(vals.get("hysteresis", "0")))
                prm["timeout"] = max(prm["poll"], int(vals.get("timeout", "1500")))
            except Exception:
                raise ValueError("line %d: bad STATELOOP timing" % line_no)
            raw_routes = vals.get("routes", "")
            routes = []
            for raw_route in raw_routes.split(","):
                bits = raw_route.split(":")
                if len(bits) != 4 or not bits[0] or not bits[3].endswith(".txt"):
                    raise ValueError("line %d: bad STATELOOP route '%s'" % (line_no, raw_route))
                try:
                    lo, hi = int(bits[1]), int(bits[2])
                except Exception:
                    raise ValueError("line %d: bad STATELOOP lux range" % line_no)
                if hi < lo:
                    lo, hi = hi, lo
                routes.append({"id": bits[0], "lo": lo, "hi": hi, "file": bits[3]})
            if not routes:
                raise ValueError("line %d: STATELOOP needs routes=" % line_no)
            prm["routes"] = routes
            prm["fallback"] = vals.get("fallback", "STOP").upper()
            if prm["fallback"] not in ("STOP", "FIRST"):
                raise ValueError("line %d: STATELOOP fallback must be STOP or FIRST" % line_no)
'''
if old not in text:
    raise SystemExit("plan_engine: parser anchor not found")
text = text.replace(old, insert + old, 1)

anchor = '# ── executor ─────────────────────────────────────────────────────────────────────────────\n'
helper = r'''# live-light-guard-v1

class _LightStateChanged(Exception):
    def __init__(self, state_id):
        self.state_id = state_id


class _LiveLightSession:
    def __init__(self, prm, ctx):
        try:
            from live_light_guard import LightStateGuard, state_spec
        except ImportError as exc:
            raise ValueError("STATELOOP needs live_light_guard.py in the portable bundle") from exc
        self.ctx = ctx
        self.prm = prm
        self.routes = {r["id"]: r for r in prm["routes"]}
        specs = [state_spec(r["id"], r["lo"], r["hi"], r["file"]) for r in prm["routes"]]
        self.guard = LightStateGuard(specs, prm["stable"], prm["hysteresis"], prm["timeout"])
        self.current = None
        self.next_poll = -1

    def _lux(self):
        reader = getattr(self.ctx, "read_lux", None)
        if reader is None:
            reader = getattr(self.ctx, "light_lux", None)
        if reader is not None:
            try:
                value = reader()
                return None if value is None else float(value)
            except Exception:
                return None
        # Compatibility fallback for the current firmware context. It probes
        # each range with the existing one-shot wait API; new firmware exposes
        # read_lux() so all ranges share one BH1750 sample.
        waiter = getattr(self.ctx, "wait_light", None)
        if waiter is None:
            return None
        for route in self.prm["routes"]:
            try:
                if waiter(route["lo"], route["hi"], 0, self.prm["poll"], 0):
                    return (route["lo"] + route["hi"]) / 2.0
            except Exception:
                return None
        return None

    def poll(self, force=False):
        now = int(self.ctx.now() * 1000)
        if not force and self.next_poll > now:
            return
        self.next_poll = now + self.prm["poll"]
        state_id = self.guard.update(self._lux(), now)
        if state_id is None:
            if self.current is not None:
                self.ctx.log("light guard unsafe - stopping")
            raise PlanAbort()
        if self.current is None:
            self.current = state_id
            self.ctx.log("light state -> " + state_id)
        elif state_id != self.current:
            old = self.current
            self.current = state_id
            self.ctx.log("light state %s -> %s" % (old, state_id))
            raise _LightStateChanged(state_id)


def _run_state_loop(prm, ctx, pos, pauses, inc):
    """Run one exported route at a time and switch only at safe step boundaries."""
    session = _LiveLightSession(prm, ctx)
    session.poll(True)
    while True:
        route = session.routes.get(session.current)
        if route is None:
            if prm["fallback"] == "FIRST":
                route = prm["routes"][0]
                session.current = route["id"]
            else:
                raise PlanAbort()
        try:
            sub = parse_plan(ctx.read_plan_file(route["file"]))
        except Exception as exc:
            ctx.log("light route failed: " + str(exc))
            raise PlanAbort()
        setattr(ctx, "_live_light_guard", session)
        try:
            run_plan(sub, ctx, _pos=pos, _pauses=pauses, _inc=inc + (route["file"],))
        except _LightStateChanged:
            # The current route was not allowed to finish another action. The
            # loop immediately loads the newly selected route.
            continue
        finally:
            if getattr(ctx, "_live_light_guard", None) is session:
                delattr(ctx, "_live_light_guard")
        session.poll(True)


'''
if anchor not in text:
    raise SystemExit("plan_engine: executor section not found")
text = text.replace(anchor, helper + anchor, 1)
ENGINE.write_text(text, encoding="utf-8")
print("patched plan_engine.py")
''