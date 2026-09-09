#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce the record's rare wide-excursion bug with the SHIPPED v1 engine.

Drives plan_move with the exact plan.txt parameters from the 14k record
(region 1301,0,378,1049 · before 120-450 · after 150-600 · mid 12:100,500 ·
idle 5,12:800,3000 · over 25 · curve 22,155 · mt 0,333 · SPEED 0,2000),
starting each move from the previous target (position persistence, like code64).

Measures, per move:
  * max consecutive-point distance (the engine's own segment length)
  * max lateral deviation from the start->target chord (excursion width)
  * max |point| distance from the region (out-of-region escape)
"""
import math, random, statistics, sys
sys.path.insert(0, "/data/code64")
import plan_engine as pe

random.seed(20260909)

REGION = (1301, 0, 378, 1049)
CFG = dict(before_min=120, before_max=450, after_min=150, after_max=600,
           mid_chance=12, mid_min=100, mid_max=500,
           idle_every_min=5, idle_every_max=12, idle_pause_min=800, idle_pause_max=3000,
           over_chance=25, curve_min=22, curve_max=155,
           speed_min=0, speed_max=2000, mt_min=0, mt_max=333)
W, H = 1920, 1080
N = 4000


def chord_dev(sx, sy, tx, ty, px, py):
    dx, dy = tx - sx, ty - sy
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return math.hypot(px - sx, py - sy)
    return abs(dx * (py - sy) - dy * (px - sx)) / L


pauses = pe.PausePlanner()
pos = [REGION[0] + REGION[2] // 2, REGION[1] + REGION[3] // 2]
max_seg = 0.0
max_dev = 0.0
worst = None
big_segs = 0
wide_paths = 0
moves_over_300_dev = 0
for m in range(N):
    tx = random.randint(REGION[0], REGION[0] + REGION[2] - 1)
    ty = random.randint(REGION[1], REGION[1] + REGION[3] - 1)
    plan = pe.plan_move(pos[0], pos[1], tx, ty, CFG, pauses, W, H)
    pts = plan["pts"]
    dev = 0.0
    for i, p in enumerate(pts):
        dev = max(dev, chord_dev(pos[0], pos[1], tx, ty, p[0], p[1]))
        if i:
            seg = math.hypot(p[0] - pts[i-1][0], p[1] - pts[i-1][1])
            if seg > max_seg:
                max_seg = seg
                worst = (m, pos[0], pos[1], tx, ty, pts[i-1], p)
            if seg > 50:
                big_segs += 1
    if dev > max_dev:
        max_dev = dev
    if dev > 300:
        moves_over_300_dev += 1
    pos = list(plan["target"])

print(f"moves simulated: {N}")
print(f"max engine segment (consecutive points): {max_seg:.1f}px")
print(f"segments > 50px: {big_segs}")
print(f"max chord deviation (path width): {max_dev:.1f}px")
print(f"paths deviating > 300px from chord: {moves_over_300_dev} ({moves_over_300_dev/N*100:.2f}%)")
if worst:
    m, sx, sy, tx, ty, a, b = worst
    print(f"worst segment in move #{m}: ({sx},{sy})->({tx},{ty}), segment {a}->{b}")

# how wide do arcs get vs plain windmouse legs? separate the two constructs
random.seed(20260909)
arc_max = leg_max = 0.0
pos = [REGION[0] + REGION[2] // 2, REGION[1] + REGION[3] // 2]
for m in range(1500):
    tx = random.randint(REGION[0], REGION[0] + REGION[2] - 1)
    ty = random.randint(REGION[1], REGION[1] + REGION[3] - 1)
    dist = math.hypot(tx - pos[0], ty - pos[1])
    # true-arc branch (curve_max>100, dist>=80): force it
    da = pe.build_arc(pos[0], pos[1], tx, ty, 1200, 22, 155, W, H)
    spine_dev = 0.0
    for p in da[0]:
        spine_dev = max(spine_dev, chord_dev(pos[0], pos[1], tx, ty, p[0], p[1]))
    arc_max = max(arc_max, spine_dev)
    # plain/overshoot leg branch: force it
    leg = pe._build_leg(pos[0], pos[1], tx, ty, 1200, 1.0, 22, 100)
    leg_dev = 0.0
    for p in leg:
        leg_dev = max(leg_dev, chord_dev(pos[0], pos[1], tx, ty, p[0], p[1]))
    leg_max = max(leg_max, leg_dev)
    pos = [tx, ty]
print(f"\nforced true-arc paths: max chord deviation {arc_max:.1f}px")
print(f"forced plain legs (windmouse): max chord deviation {leg_max:.1f}px")
