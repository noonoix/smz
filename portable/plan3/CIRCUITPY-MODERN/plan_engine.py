# Compatibility facade for the memory-split experimental bundle.
# Parsing is needed before execution, but importing the human/parallel/exec
# modules at the same time creates the highest transient heap peak on RP2040.
# Keep parse_plan/PlanAbort eager and defer the executor until the route source
# has been parsed, deleted, and collected by code.py.
import gc
from plan_engine_parse import (PlanAbort, _below, _clamp, parse_plan, rand_range)
gc.collect()

_LITE_OPS = ("PLAN", "SCREEN", "SPEED", "DELAY", "LOOP", "LOOPTIME",
             "ENDLOOP", "RMOUSE")

def _lite_rmouse(prm, ctx, pause):
    import random
    _rx, _ry, rw, rh = prm.get("region", (0, 0, ctx.screen_w, ctx.screen_h))
    sx, sy = ctx.screen_w // 2, ctx.screen_h // 2
    xlim = max(1, min(max(1, rw - 1), max(32, ctx.screen_w // 4)))
    ylim = max(1, min(max(1, rh - 1), max(32, ctx.screen_h // 4)))
    xmag = random.randint(max(1, xlim // 3), xlim)
    ymag = random.randint(max(1, ylim // 3), ylim)
    tx = sx + (xmag if random.randint(0, 1) else -xmag)
    ty = sy + (ymag if random.randint(0, 1) else -ymag)
    dx, dy = tx - sx, ty - sy
    span = max(abs(dx), abs(dy))

    curve = prm.get("curve", (15, 45))
    cmin, cmax = curve
    if cmax < cmin:
        cmin, cmax = cmax, cmin
    amp = min(span // 3, (span * rand_range(int(cmin), int(cmax))) // 100)
    if _below(2) == 0:
        amp = -amp
    denom = max(1, span)
    pxoff, pyoff = (-dy * amp) // denom, (dx * amp) // denom

    mt = prm.get("mt", (0, 0))
    speed = prm.get("speed", (ctx.speed_min, ctx.speed_max))
    if mt[1] > 0:
        total = rand_range(mt[0], mt[1])
    elif speed[1] > 0:
        sampled = rand_range(max(1, speed[0]), max(max(1, speed[0]), speed[1]))
        path = max(abs(dx), abs(dy)) + min(abs(dx), abs(dy)) // 2
        total = max(0, (path * 1000) // sampled - path)
    else:
        total = 0
    spatial = max(8, (span + 11) // 12)
    timed = (total + 7) // 8 if total > 0 else spatial
    segments = max(8, min(128, max(spatial, timed)))
    base, extra = total // segments, total % segments

    before = prm.get("before", (120, 450))
    after = prm.get("after", (150, 600))
    mid = prm.get("mid", (12, (100, 400)))
    mid_ms = rand_range(mid[1][0], mid[1][1]) if mid[0] > 0 and _below(100) < mid[0] else 0
    mid_at = 1 + _below(max(1, segments - 1))
    if before[1] > 0 and not ctx.sleep_ms(rand_range(before[0], before[1])):
        raise PlanAbort()

    ctx.log("rmouse-rel-stream -> (%+d,%+d) <=128 pts" % (dx, dy))
    px, py = sx, sy
    for step in range(1, segments + 1):
        if not ctx.gate():
            raise PlanAbort()
        t = (step * 1024) // segments
        ease = (t * t * (3072 - 2 * t)) // 1048576
        bow = (4 * t * (1024 - t)) // 1024
        nx = sx + (dx * ease + pxoff * bow) // 1024
        ny = sy + (dy * ease + pyoff * bow) // 1024
        if step == segments:
            nx, ny = tx, ty
        if nx != px or ny != py:
            ctx.mmove_relative(nx - px, ny - py)
        delay = base + (1 if step <= extra else 0)
        if mid_ms and step == mid_at:
            delay += mid_ms
        if delay and not ctx.sleep_ms(delay):
            raise PlanAbort()
        px, py = nx, ny
    if after[1] > 0 and not ctx.sleep_ms(rand_range(after[0], after[1])):
        raise PlanAbort()

    idle = prm.get("idle", ((5, 12), (1000, 5000)))
    if idle[1][1] > 0 and idle[0][1] > 0:
        pause[0] += 1
        if pause[1] < 0:
            pause[1] = max(1, rand_range(idle[0][0], idle[0][1]))
        if pause[0] >= pause[1]:
            pause[0] = 0
            pause[1] = max(1, rand_range(idle[0][0], idle[0][1]))
            wait = rand_range(idle[1][0], idle[1][1])
            ctx.log("idle break %d ms" % wait)
            if not ctx.sleep_ms(wait):
                raise PlanAbort()

def _run_lite(plan, ctx):
    pause = [0, -1]
    stack = []
    i = 0
    while i < len(plan):
        if not ctx.gate():
            raise PlanAbort()
        op, prm = plan[i]
        if op == "PLAN":
            pass
        elif op == "SCREEN":
            ctx.screen_w, ctx.screen_h = prm["v"]
            setter = getattr(ctx, "setres", None)
            if setter is not None:
                setter(prm["v"][0], prm["v"][1])
        elif op == "SPEED":
            ctx.speed_min, ctx.speed_max = prm["v"]
        elif op == "DELAY":
            if not ctx.sleep_ms(rand_range(*prm["v"])):
                raise PlanAbort()
        elif op == "LOOP":
            stack.append([i, prm["n"], None])
        elif op == "LOOPTIME":
            stack.append([i, 0, ctx.now() + prm["sec"]])
        elif op == "ENDLOOP":
            top = stack[-1]
            if top[2] is not None:
                if ctx.now() < top[2]:
                    i = top[0]
                else:
                    stack.pop()
            elif top[1] == 0:
                i = top[0]
            else:
                top[1] -= 1
                if top[1] > 0:
                    i = top[0]
                else:
                    stack.pop()
        elif op == "RMOUSE":
            _lite_rmouse(prm, ctx, pause)
        i += 1

def run_plan(plan, ctx):
    if (getattr(ctx, "mouse_mode", "") == "relative"
            and all(op in _LITE_OPS for op, _prm in plan)):
        ctx.log("plan-lite-relative")
        return _run_lite(plan, ctx)
    gc.collect()
    import plan_engine_exec as executor
    # Random Package shuffle uses the shared C#-compatible helper.
    executor._below = _below
    return executor.run_plan(plan, ctx)
