"""PLAN v0.9.67 root auto-cycle adapter.

Keeps cycle policy and Resume Essentials root-scoped while the existing plan
engine executes ordinary ops and INCLUDE files against one shared deadline.
"""
import random
import time

import plan_engine
from cycle_runtime import PlanDeadline, RootCycle


def _pair(body, line_no, name):
    p = body.split(",")
    if len(p) != 2:
        raise ValueError("line %d: %s needs min,max seconds" % (line_no, name))
    try:
        lo, hi = int(p[0]), int(p[1])
    except Exception:
        raise ValueError("line %d: bad %s range" % (line_no, name))
    if hi < lo:
        lo, hi = hi, lo
    if lo <= 0:
        raise ValueError("line %d: %s range must be positive" % (line_no, name))
    return lo, hi


def _nonnegative_pair(body, line_no, name):
    p = body.split(",")
    if len(p) != 2:
        raise ValueError("line %d: %s needs min,max seconds" % (line_no, name))
    try:
        lo, hi = int(p[0]), int(p[1])
    except Exception:
        raise ValueError("line %d: bad %s range" % (line_no, name))
    if hi < lo:
        lo, hi = hi, lo
    if lo < 0:
        raise ValueError("line %d: %s range cannot be negative" % (line_no, name))
    return lo, hi


def parse_cycle_plan(text):
    """Return (ordinary_ops, policy). Directives are valid only in the root plan."""
    kept = []
    runfor = None
    autoresume = None
    postlaunch = None
    seen_plan = False
    seen_work = False
    for line_no, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            kept.append(raw)
            continue
        op, _sep, body = line.partition("|")
        op = op.upper()
        if op == "PLAN":
            if seen_plan:
                raise ValueError("line %d: duplicate PLAN" % line_no)
            seen_plan = True
            kept.append(raw)
            continue
        if op in ("RUNFOR", "AUTORESUME", "POSTLAUNCH"):
            if not seen_plan or seen_work:
                raise ValueError("line %d: %s must be a root header directive" % (line_no, op))
            if op == "RUNFOR":
                if runfor is not None:
                    raise ValueError("line %d: duplicate RUNFOR" % line_no)
                runfor = _pair(body, line_no, op)
            elif op == "AUTORESUME":
                if autoresume is not None:
                    raise ValueError("line %d: duplicate AUTORESUME" % line_no)
                p = body.split(",")
                if len(p) != 3 or p[0] not in ("0", "1"):
                    raise ValueError("line %d: AUTORESUME needs 0|1,min,max seconds" % line_no)
                autoresume = (p[0] == "1",) + _pair(",".join(p[1:]), line_no, op)
            else:
                if postlaunch is not None:
                    raise ValueError("line %d: duplicate POSTLAUNCH" % line_no)
                p = body.split(",")
                if len(p) != 6 or p[0] not in ("0", "1"):
                    raise ValueError(
                        "line %d: POSTLAUNCH needs 0|1,slot,beforeMin,beforeMax,afterMin,afterMax"
                        % line_no)
                try:
                    slot = int(p[1])
                except Exception:
                    raise ValueError("line %d: bad POSTLAUNCH taskbar slot" % line_no)
                if not 1 <= slot <= 9:
                    raise ValueError("line %d: POSTLAUNCH taskbar slot must be 1..9" % line_no)
                before = _nonnegative_pair(",".join(p[2:4]), line_no, "POSTLAUNCH before")
                after = _nonnegative_pair(",".join(p[4:6]), line_no, "POSTLAUNCH after")
                postlaunch = (p[0] == "1", slot, before, after)
            continue
        seen_work = True
        kept.append(raw)
    if runfor is None and autoresume is None and postlaunch is None:
        return plan_engine.parse_plan(text), None
    if runfor is None or autoresume is None:
        raise ValueError("RUNFOR and AUTORESUME must be specified together")
    return plan_engine.parse_plan("\n".join(kept)), {
        "run": runfor,
        "auto": autoresume[0],
        "resume": autoresume[1:],
        "launch": postlaunch or (False, 1, (0, 0), (0, 0)),
    }


class _CycleContext:
    """Proxy checking deadline and recurring essentials only at safe boundaries."""
    def __init__(self, inner, cycle, essentials=None):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_cycle", cycle)
        object.__setattr__(self, "_essentials", essentials)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        if name in ("_inner", "_cycle", "_essentials"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._inner, name, value)

    def gate(self):
        self._cycle.gate()
        base = getattr(self._inner, "gate", None)
        if base is not None and not base():
            return False
        if self._essentials is not None:
            try:
                self._essentials.run_due(self)
            except Exception as exc:
                try:
                    from resume_essentials_runtime import EssentialAbort
                    if isinstance(exc, EssentialAbort):
                        raise plan_engine.PlanAbort()
                except ImportError:
                    pass
                raise
        self._cycle.gate()
        return True

    def sleep_ms(self, ms):
        left = max(0, int(ms))
        while left > 0:
            self._cycle.gate()
            part = min(40, left)
            sleeper = getattr(self._inner, "sleep_ms", None)
            if sleeper is not None:
                if not sleeper(part):
                    return False
            else:
                time.sleep(part / 1000.0)
            left -= part
        self._cycle.gate()
        return True


def _post_restart_launch(ctx, rng, policy):
    """Launch one pinned taskbar app before Resume Essentials on auto-resume only."""
    enabled, slot, before, after = policy
    if not enabled:
        return
    release = getattr(ctx, "release_all", None) or getattr(ctx, "halt", None)
    if release is not None:
        release()
    ctx.log("cycle: Restart Launch waiting before Win+%d" % slot)
    if not ctx.sleep_ms(rng.randint(before[0], before[1]) * 1000):
        raise plan_engine.PlanAbort()
    win, number = 91, 48 + slot
    ctx.kdown(win)
    try:
        if not ctx.sleep_ms(rng.randint(35, 75)):
            raise plan_engine.PlanAbort()
        ctx.kdown(number)
        try:
            if not ctx.sleep_ms(rng.randint(55, 110)):
                raise plan_engine.PlanAbort()
        finally:
            ctx.kup(number)
        if not ctx.sleep_ms(rng.randint(30, 70)):
            raise plan_engine.PlanAbort()
    finally:
        ctx.kup(win)
    ctx.log("cycle: Restart Launch sent Win+%d" % slot)
    if not ctx.sleep_ms(rng.randint(after[0], after[1]) * 1000):
        raise plan_engine.PlanAbort()


def run_root(text, ctx, rng=None, arm_store=None):
    """Run one root cycle. Returns 'finished', 'expired' or propagates ordinary errors/abort."""
    ops, policy = parse_cycle_plan(text)
    if policy is None:
        plan_engine.run_plan(ops, ctx)
        return "finished"
    cycle = RootCycle(getattr(ctx, "now", None), rng, arm_store)
    cycle.configure(policy["run"][0], policy["run"][1],
                    policy["auto"], policy["resume"][0], policy["resume"][1])
    cycle.start()
    essentials = getattr(ctx, "resume_essentials", None)
    is_auto_resume = bool(getattr(essentials, "resume_pending", False))
    wrapped = _CycleContext(ctx, cycle, essentials)
    try:
        if is_auto_resume:
            _post_restart_launch(wrapped, rng or random, policy["launch"])
        if essentials is not None:
            try:
                essentials.run_resume(wrapped)
            except Exception as exc:
                try:
                    from resume_essentials_runtime import EssentialAbort
                    if isinstance(exc, EssentialAbort):
                        raise plan_engine.PlanAbort()
                except ImportError:
                    pass
                raise
        plan_engine.run_plan(ops, wrapped)
        return "finished"
    except PlanDeadline:
        release = getattr(ctx, "release_all", None) or getattr(ctx, "halt", None)
        if release is None:
            raise RuntimeError("cycle expiry requires release_all/halt")
        if not cycle.arm_natural_restart(release):
            raise
        restart = getattr(ctx, "restart_windows", None)
        if restart is not None:
            restart()
        else:
            import restart_windows
            restart_windows.perform(ctx, rng)
        return "expired"
