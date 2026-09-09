#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Second pass: pin down what 'mouse links after Start' is, numerically."""
import re, statistics

text = open("/data/record-14k.txt", "rb").read().decode("utf-16")
lines = [l.strip() for l in text.split("\r\n") if l.strip()]

events, t = [], 0.0
for l in lines:
    if l.startswith("Delay"):
        m = re.search(r"([\d.]+)\s*ms", l)
        if m: t += float(m.group(1))
    elif l.startswith("Key Down"):
        events.append((t, "down", l.split(":", 1)[1].strip()))
    elif l.startswith("Key Up"):
        events.append((t, "up", l.split(":", 1)[1].strip()))
    elif l.startswith("Mouse Position"):
        m = re.search(r"X:(\d+)\s+Y:(\d+)", l)
        if m: events.append((t, "pos", (int(m.group(1)), int(m.group(2)))))

starts = [tt for (tt, k, v) in events if k == "down" and "Num" in v][0::2]
pos = [(tt, p) for (tt, k, p) in events if k == "pos"]

# ── 1) stalls: duration distribution + distance from nearest preceding Start ──
print("── stalls >= 300 ms (context: idle breaks are designed 800-3000ms every 5-12 moves) ──")
stall_rows = []
for (t0, p0), (t1, p1) in zip(pos, pos[1:]):
    dt = t1 - t0
    if dt >= 300:
        since = min((t0 - s) for s in starts if s <= t0) if any(s <= t0 for s in starts) else -1
        stall_rows.append((t0, dt, since))
print(f"count: {len(stall_rows)}")
buckets = {"300-800ms": 0, "0.8-3s": 0, "3-5s": 0, ">5s": 0}
for _, dt, _ in stall_rows:
    if dt < 800: buckets["300-800ms"] += 1
    elif dt < 3000: buckets["0.8-3s"] += 1
    elif dt < 5000: buckets["3-5s"] += 1
    else: buckets[">5s"] += 1
print("duration buckets:", buckets)
near = [r for r in stall_rows if 0 <= r[2] <= 3000]
print(f"stalls within 3s after a Start: {len(near)}")
for t0, dt, since in near:
    print(f"   t={t0/1000:.1f}s  stall {dt:.0f}ms  ({since:.0f}ms after Start)")

# ── 2) big steps (>50px between consecutive samples) ──
print("\n── big steps (>50px) ──")
big = []
for (t0, p0), (t1, p1) in zip(pos, pos[1:]):
    d = ((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2) ** 0.5
    dt = t1 - t0
    if d > 50:
        since = min((t0 - s) for s in starts if s <= t0) if any(s <= t0 for s in starts) else -1
        big.append((t0, p0, p1, d, dt, since))
print(f"count: {len(big)}")
for t0, p0, p1, d, dt, since in big:
    print(f"   t={t0/1000:.1f}s  {p0}->{p1}  {d:.0f}px in {dt:.0f}ms  ({since:.0f}ms after Start)")

# ── 3) repeated-position runs (cursor truly stuck while plan should move it) ──
print("\n── consecutive identical positions (stuck signature) ──")
runs, cur = [], [pos[0]]
for e in pos[1:]:
    if e[1] == cur[-1][1]: cur.append(e)
    else:
        if len(cur) >= 20: runs.append((cur[0][0], cur[-1][0], len(cur), cur[0][1]))
        cur = [e]
if len(cur) >= 20: runs.append((cur[0][0], cur[-1][0], len(cur), cur[0][1]))
print(f"runs of >=20 identical consecutive positions: {len(runs)}")
for t0, t1, n, p in runs[:15]:
    since = min((t0 - s) for s in starts if s <= t0) if any(s <= t0 for s in starts) else -1
    print(f"   t={t0/1000:.1f}s..{t1/1000:.1f}s  {n} identical samples at {p}  ({(t1-t0):.0f}ms, {since:.0f}ms after Start)")

# ── 4) first 3 seconds after each Start: what the cursor does ──
print("\n── first 3s after each Start ──")
for i, s in enumerate(starts):
    win = [(tt, p) for (tt, p) in pos if s <= tt <= s + 3000]
    if len(win) < 2:
        print(f"start #{i+1}: NO mouse movement in first 3s") 
        continue
    dists = [((b[1][0]-a[1][0])**2 + (b[1][1]-a[1][1])**2)**.5 for a, b in zip(win, win[1:])]
    gaps = [b[0]-a[0] for a, b in zip(win, win[1:])]
    travel = sum(dists)
    maxgap = max(gaps)
    print(f"start #{i+1}: {len(win)} samples, travel {travel:.0f}px, max gap {maxgap:.0f}ms, first sample at +{win[0][0]-s:.0f}ms")
