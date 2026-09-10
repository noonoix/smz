# Generated from canonical plan_engine.py; do not hand-edit.
import time
import math
import random

def _save_mouse_pos(ctx, pos):
    setter = getattr(ctx, 'set_mouse_pos', None)
    if setter is not None:
        setter(int(pos[0]), int(pos[1]))

def _rf():
    return random.random()

def _below(n):
    return random.randrange(n) if n > 0 else 0

def rand_range(mn, mx):
    if mx < mn:
        mn, mx = (mx, mn)
    if mx <= 0:
        return 0
    return mn if mx <= mn else random.randint(mn, mx)

def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def tuned_wind(dist, curve):
    cv = 0.3 if curve < 0 else _clamp(curve, 0.0, 2.0)
    base = 0.3 + cv * 3.0 if cv < 1.0 else 3.3 + (cv - 1.0) * 4.7
    return base * _clamp(dist / 400.0, 0.35, 1.0)

def build_range_profile(mn, mx, knot_count, low_ends=False):
    if mx < mn:
        mn, mx = (mx, mn)
    knot_count = int(_clamp(knot_count, 2, 12))
    if abs(mx - mn) < 1e-09:
        return [float(mn)] * knot_count
    span = mx - mn
    knots = []
    upper = _below(2) == 1
    for i in range(knot_count):
        force_low = low_ends and (i == 0 or i == knot_count - 1)
        band = _rf() * 0.18 if force_low else 0.6 + _rf() * 0.4 if upper else _rf() * 0.4
        knots.append(mn + span * band)
        upper = not upper
    return knots

def sample_profile(knots, t):
    if not knots:
        return 0.0
    if len(knots) == 1:
        return knots[0]
    p = _clamp(t, 0.0, 1.0) * (len(knots) - 1)
    i = min(len(knots) - 2, int(math.floor(p)))
    u = p - i
    smooth = u * u * (3.0 - 2.0 * u)
    return knots[i] + (knots[i + 1] - knots[i]) * smooth

def _poly_len(pts):
    total = 0.0
    for i in range(1, len(pts)):
        total += math.sqrt((pts[i][0] - pts[i - 1][0]) ** 2 + (pts[i][1] - pts[i - 1][1]) ** 2)
    return total

def windmouse(sx, sy, tx, ty, wind, gravity, curve, profile):
    sqrt3, sqrt5 = (math.sqrt(3.0), math.sqrt(5.0))
    x, y = (float(sx), float(sy))
    vx = vy = wx = wy = 0.0
    dist0 = max(1.0, math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2))
    if dist0 < 3:
        return [[tx, ty, 0]]
    max_step = _clamp(dist0 / 15.0, 6.0, 30.0)
    stop_radius = min(8.0, max(2.0, dist0 * 0.02))
    pts = []
    guard = 0
    while guard < 2000:
        guard += 1
        dist = math.sqrt((tx - x) ** 2 + (ty - y) ** 2)
        if dist < stop_radius:
            break
        live_wind = wind
        if profile:
            progress = _clamp(1.0 - dist / dist0, 0.0, 1.0)
            live_wind = tuned_wind(dist0, sample_profile(profile, progress) / 100.0)
        wmag = min(live_wind, dist)
        if dist >= stop_radius * 4:
            wx = wx / sqrt3 + (2 * _rf() - 1) * wmag / sqrt5
            wy = wy / sqrt3 + (2 * _rf() - 1) * wmag / sqrt5
        else:
            wx /= sqrt3
            wy /= sqrt3
            max_step = max(2.5, max_step / sqrt5)
        vx += wx + gravity * (tx - x) / dist
        vy += wy + gravity * (ty - y) / dist
        vmag = math.sqrt(vx * vx + vy * vy)
        if vmag > max_step:
            vx = vx / vmag * max_step
            vy = vy / vmag * max_step
        x += vx
        y += vy
        pts.append([int(round(x)), int(round(y)), 0])
    pts.append([tx, ty, 0])
    return pts

def resample_variable(spine, mn_sp, mx_sp):
    if not spine:
        return []
    if len(spine) == 1:
        return [list(spine[0])]
    if mx_sp < mn_sp:
        mn_sp, mx_sp = (mx_sp, mn_sp)
    mn_sp = max(0.5, mn_sp)
    mx_sp = max(mn_sp, mx_sp)
    total = _poly_len(spine)
    if total < 1e-06:
        return [list(spine[-1])]
    profile = build_range_profile(mn_sp, mx_sp, 5)
    outp = []
    next_at = sample_profile(profile, 0.0)
    acc = 0.0
    for i in range(1, len(spine)):
        x0, y0 = (spine[i - 1][0], spine[i - 1][1])
        seg = math.sqrt((spine[i][0] - x0) ** 2 + (spine[i][1] - y0) ** 2)
        if seg < 1e-06:
            continue
        while acc + seg >= next_at:
            u = (next_at - acc) / seg
            outp.append([int(round(x0 + (spine[i][0] - x0) * u)), int(round(y0 + (spine[i][1] - y0) * u)), 0])
            phase = _clamp(next_at / total, 0.0, 1.0)
            next_at += max(0.5, sample_profile(profile, phase))
        acc += seg
    last = spine[-1]
    if not outp or outp[-1][0] != last[0] or outp[-1][1] != last[1]:
        outp.append([last[0], last[1], 0])
    return outp

def assign_dynamic_delays(pts, sx, sy, smin, smax, target_ms=0):
    for p in pts:
        p[2] = 0
    if not pts or (smax <= 0 and target_ms <= 0):
        return
    shape_only = smax <= 0
    lo = 150 if shape_only else max(150, min(smin, smax))
    hi = 2000 if shape_only else max(lo, max(smin, smax))
    knot_count = int(_clamp(4 + len(pts) // 120, 4, 9))
    prof = build_range_profile(float(lo), float(hi), knot_count, low_ends=True)
    segs = []
    path = 0.0
    px, py = (sx, sy)
    for p in pts:
        s = math.sqrt((p[0] - px) ** 2 + (p[1] - py) ** 2)
        segs.append(s)
        path += s
        px, py = (p[0], p[1])
    if path < 1e-06:
        return
    weights = []
    wsum = 0.0
    travelled = 0.0
    for i in range(len(pts)):
        phase = _clamp((travelled + segs[i] * 0.5) / path, 0.0, 1.0)
        speed = _clamp(sample_profile(prof, phase), lo, hi)
        w = segs[i] * 1000.0 / max(1.0, speed)
        weights.append(w)
        wsum += w
        travelled += segs[i]
    if wsum <= 0:
        return
    scale = target_ms / wsum if target_ms > 0 else 1.0
    for i in range(len(pts)):
        pts[i][2] = max(1, int(round(weights[i] * scale)))

def curve_height_ratio(pct):
    p = _clamp(float(pct), 0.0, 200.0)
    if p <= 100.0:
        return 0.08 * (p / 100.0) ** 1.15
    return 0.08 + 0.42 * math.sqrt((p - 100.0) / 100.0)

def _ray_to_edge(x, y, dx, dy, w, h, margin):
    max_x = max(margin, w - 1.0 - margin)
    max_y = max(margin, h - 1.0 - margin)
    limit = float('inf')
    if abs(dx) > 1e-09:
        limit = min(limit, (max_x - x) / dx if dx > 0 else (margin - x) / dx)
    if abs(dy) > 1e-09:
        limit = min(limit, (max_y - y) / dy if dy > 0 else (margin - y) / dy)
    return max(0.0, limit) if limit != float('inf') else 0.0

def build_arc(sx, sy, tx, ty, total_ms, cmin, cmax, w, h):
    dx, dy = (tx - sx, ty - sy)
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 3:
        return ([[tx, ty, max(0, total_ms)]], 0.0, total_ms)
    cmin = _clamp(cmin, 0, 200)
    cmax = _clamp(cmax, 0, 200)
    if cmax < cmin:
        cmin, cmax = (cmax, cmin)
    ux, uy = (dx / dist, dy / dist)
    nx, ny = (-uy, ux)
    skew = _rf() * 0.14 - 0.07
    wobble = 0.025 + _rf() * 0.045
    phase0 = _rf() * math.pi * 2.0
    samples = int(_clamp(math.ceil(dist / 12.0), 32, 240))
    knot_count = int(_clamp(4 + int(dist / 320.0), 4, 8))
    knots = build_range_profile(cmin, cmax, knot_count)

    def fit_for_side(side):
        fit = 1.0
        for i in range(1, samples):
            t = i / samples
            q = _clamp(t + skew * math.sin(math.pi * t), 0.0, 1.0)
            along = 0.5 - 0.5 * math.cos(math.pi * q)
            shape = math.sin(math.pi * q) * (1.0 + wobble * math.sin(2.0 * math.pi * t + phase0))
            bx = sx + ux * dist * along
            by = sy + uy * dist * along
            required = dist * curve_height_ratio(sample_profile(knots, t)) * max(0.0, shape)
            if required < 1e-06:
                continue
            room = _ray_to_edge(bx, by, nx * side, ny * side, w, h, 2.0)
            fit = min(fit, room / required)
        return _clamp(fit * 0.94, 0.0, 1.0)
    fit_pos, fit_neg = (fit_for_side(+1), fit_for_side(-1))
    if fit_pos >= 0.9 and fit_neg >= 0.9:
        side = -1 if _below(2) == 0 else +1
        fit = fit_pos if side > 0 else fit_neg
    elif fit_pos >= fit_neg:
        side, fit = (+1, fit_pos)
    else:
        side, fit = (-1, fit_neg)
    spine = [[sx, sy, 0]]
    actual_height = 0.0
    for i in range(1, samples):
        t = i / samples
        q = _clamp(t + skew * math.sin(math.pi * t), 0.0, 1.0)
        along = 0.5 - 0.5 * math.cos(math.pi * q)
        shape = math.sin(math.pi * q) * (1.0 + wobble * math.sin(2.0 * math.pi * t + phase0))
        local_h = dist * curve_height_ratio(sample_profile(knots, t)) * fit
        normal = side * local_h * max(0.0, shape)
        actual_height = max(actual_height, abs(normal))
        spine.append([int(round(sx + ux * dist * along + nx * normal)), int(round(sy + uy * dist * along + ny * normal)), 0])
    spine.append([tx, ty, 0])
    path_len = _poly_len(spine)
    arc_ms = 0 if total_ms <= 0 else int(_clamp(round(total_ms * max(1.0, path_len / dist)), 60, 30000))
    scale = max(1.0, dist / 2500.0)
    return (resample_variable(spine, 2.0 * scale, 3.2 * scale), actual_height, arc_ms)
_DEFAULT_CFG = dict(before_min=120, before_max=450, after_min=150, after_max=600, mid_chance=12, mid_min=100, mid_max=400, idle_every_min=5, idle_every_max=12, idle_pause_min=1000, idle_pause_max=5000, over_chance=15, curve_min=15, curve_max=45, speed_min=0, speed_max=2000, mt_min=0, mt_max=0)

def plan_move(sx, sy, tx, ty, c, pauses, w, h):
    tx = int(_clamp(tx, 0, max(0, w - 1)))
    ty = int(_clamp(ty, 0, max(0, h - 1)))
    sx = int(_clamp(sx, 0, max(0, w - 1)))
    sy = int(_clamp(sy, 0, max(0, h - 1)))
    dist = math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2)
    speed_lo = max(150, c['speed_min'])
    speed_hi = max(speed_lo, c['speed_max'])
    total_ms = 0 if c['speed_max'] <= 0 else int(_clamp(dist * 1000.0 / max(1.0, (speed_lo + speed_hi) / 2.0), 60, 30000))
    curve_min = int(_clamp(c['curve_min'], 0, 200))
    curve_max = int(_clamp(c['curve_max'], 0, 200))
    if curve_max < curve_min:
        curve_min, curve_max = (curve_max, curve_min)
    sampled = curve_min if curve_max == curve_min else random.randint(curve_min, curve_max)
    curve = _clamp(sampled / 100.0, 0.0, 2.0)
    mt_min, mt_max = (max(0, c['mt_min']), max(0, c['mt_max']))
    if mt_max < mt_min:
        mt_min, mt_max = (mt_max, mt_min)
    target_ms = rand_range(max(1, mt_min), max(1, mt_max)) if mt_max > 0 else 0
    dense = []
    overshoot_idx = -1
    if curve_max > 100 and dist >= 80:
        dense, _height, _arc_ms = build_arc(sx, sy, tx, ty, total_ms, curve_min, curve_max, w, h)
    elif dist >= 60 and c['over_chance'] > 0 and (_below(100) < c['over_chance']):
        ux, uy = ((tx - sx) / dist, (ty - sy) / dist)
        cscale = min(1.0, curve)
        over = int(_clamp(dist * (0.03 + _rf() * 0.05) * cscale, 2, 20))
        perp = int(_rf() * (2.0 + cscale * 5.0) - (1.0 + cscale * 2.5))
        ox = int(_clamp(tx + int(ux * over - uy * perp), 0, max(0, w - 1)))
        oy = int(_clamp(ty + int(uy * over + ux * perp), 0, max(0, h - 1)))
        leg1_ms = max(40, int(total_ms * 0.8))
        leg2_ms = max(30, total_ms - leg1_ms)
        dense += _build_leg(sx, sy, ox, oy, leg1_ms, curve, curve_min, curve_max)
        overshoot_idx = len(dense) - 1
        dense += _build_leg(ox, oy, tx, ty, leg2_ms, curve, curve_min, curve_max)
    else:
        dense = _build_leg(sx, sy, tx, ty, total_ms, curve, curve_min, curve_max)
    for p in dense:
        p[0] = int(_clamp(p[0], 0, max(0, w - 1)))
        p[1] = int(_clamp(p[1], 0, max(0, h - 1)))
    assign_dynamic_delays(dense, sx, sy, c['speed_min'], c['speed_max'], target_ms)
    if overshoot_idx >= 0:
        dense[overshoot_idx][2] += rand_range(60, 180)
    mid = pauses.mid_pause(c)
    if mid > 0 and len(dense) >= 8:
        dense[2 + _below(len(dense) - 4)][2] += mid
    return {'before': rand_range(c['before_min'], c['before_max']), 'after': rand_range(c['after_min'], c['after_max']), 'long': pauses.roll_long(c), 'target': (tx, ty), 'pts': dense}

def _build_leg(sx, sy, tx, ty, total_ms, curve, cmin, cmax):
    dist0 = max(1.0, math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2))
    profile = None
    if cmin >= 0 and cmax >= 0:
        profile = build_range_profile(cmin, cmax, int(_clamp(4 + int(dist0 / 320.0), 4, 8)))
    spine = windmouse(sx, sy, tx, ty, tuned_wind(dist0, curve), 14.0, curve, profile)
    with_start = [[sx, sy, 0]] + spine
    scale = max(1.0, dist0 / 2500.0)
    return resample_variable(with_start, 2.0 * scale, 3.2 * scale)

def _exec_rmouse(prm, ctx, pauses, pos, target=None):
    rx, ry, rw, rh = prm.get('region', (0, 0, ctx.screen_w, ctx.screen_h))
    c = dict(_DEFAULT_CFG)
    c['speed_min'], c['speed_max'] = (ctx.speed_min, ctx.speed_max)
    if 'mt' in prm:
        c['mt_min'], c['mt_max'] = prm['mt']
    if 'curve' in prm:
        c['curve_min'], c['curve_max'] = prm['curve']
    if 'before' in prm:
        c['before_min'], c['before_max'] = prm['before']
    if 'after' in prm:
        c['after_min'], c['after_max'] = prm['after']
    if 'mid' in prm:
        c['mid_chance'], (c['mid_min'], c['mid_max']) = prm['mid']
    if 'idle' in prm:
        (c['idle_every_min'], c['idle_every_max']), (c['idle_pause_min'], c['idle_pause_max']) = prm['idle']
    if 'over' in prm:
        c['over_chance'] = prm['over']
    if target is None:
        tx = random.randint(rx, rx + max(0, rw - 1))
        ty = random.randint(ry, ry + max(0, rh - 1))
    else:
        tx, ty = target
    if prm.get('human', 1) == 0:
        ctx.mmove(tx, ty)
        pos[0], pos[1] = (tx, ty)
        _save_mouse_pos(ctx, pos)
        return
    plan = plan_move(pos[0], pos[1], tx, ty, c, pauses, ctx.screen_w, ctx.screen_h)
    ctx.log('rmouse -> (%d,%d) %d pts' % (tx, ty, len(plan['pts'])))
    if not ctx.sleep_ms(plan['before']):
        raise PlanAbort()
    for pt in plan['pts']:
        ctx.mmove(pt[0], pt[1])
        pos[0], pos[1] = (pt[0], pt[1])
        _save_mouse_pos(ctx, pos)
        if not ctx.sleep_ms(pt[2]):
            raise PlanAbort()
    pos[0], pos[1] = plan['target']
    _save_mouse_pos(ctx, pos)
    if not ctx.sleep_ms(plan['after']):
        raise PlanAbort()
    if plan['long'] > 0:
        ctx.log('idle break %d ms' % plan['long'])
        if not ctx.sleep_ms(plan['long']):
            raise PlanAbort()
