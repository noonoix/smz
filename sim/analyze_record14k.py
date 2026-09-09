#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze the 14k-entry board-output record: mouse behaviour around plan Start events.

Focus: the user's report "sometimes after Start the mouse jumps/links" — quantify:
  1) Start/Stop cycle detection (Num Lock = start/stop, Scroll Lock = pause)
  2) first-move distance after each Start (stale-position jump signature)
  3) teleports (>400px in <100ms — golden standard: human = 0)
  4) step-size distribution, cadence, stalls (gaps), phantom clicks
"""
import re, statistics, sys

raw = open("/data/record-14k.txt", "rb").read()
text = raw.decode("utf-16")
lines = [l.strip() for l in text.split("\r\n") if l.strip()]
print("total lines:", len(lines))

# ── parse to a timed event list ──────────────────────────────────────────────
events = []          # (t_ms, kind, payload)
t = 0.0
key_down = key_up = mouse_pos = mouse_event = delay_n = 0
for l in lines:
    if l.startswith("Delay"):
        m = re.search(r"([\d.]+)\s*ms", l)
        if m:
            t += float(m.group(1)); delay_n += 1
    elif l.startswith("Key Down"):
        events.append((t, "down", l.split(":", 1)[1].strip())); key_down += 1
    elif l.startswith("Key Up"):
        events.append((t, "up", l.split(":", 1)[1].strip())); key_up += 1
    elif l.startswith("Mouse Position"):
        m = re.search(r"X:(\d+)\s+Y:(\d+)", l)
        if m:
            events.append((t, "pos", (int(m.group(1)), int(m.group(2))))); mouse_pos += 1
    elif l.startswith("Mouse Event"):
        events.append((t, "mev", l.split(":", 1)[1].strip())); mouse_event += 1
print(f"parsed: {key_down} key-down, {key_up} key-up, {mouse_pos} mouse-pos, {mouse_event} mouse-event, {delay_n} delays")
print(f"recorded span: {t/1000:.1f} s")

keys = {}
for _, k, v in events:
    if k in ("down", "up"):
        keys[v] = keys.get(v, 0) + 1
print("keys seen:", keys)
mevs = {}
for _, k, v in events:
    if k == "mev":
        mevs[v] = mevs.get(v, 0) + 1
print("mouse events:", mevs)

# ── Start/Stop cycles via Num Lock edges ─────────────────────────────────────
numlock_edges = [ev for ev in events if ev[1] == "down" and "Num" in ev[2]]
print("\nNum Lock down edges (plan Start/Stop toggles):", len(numlock_edges))
starts = numlock_edges[0::2]   # alternating start/stop — odd count handled below
print("assuming alternating start/stop -> start events:", len(starts))

# mouse position immediately BEFORE each start and first move AFTER
print("\n── per-Start first-move analysis ──")
first_jump = []
for idx, (st, _, _) in enumerate(starts):
    before = [p for (tt, k, p) in events if k == "pos" and tt < st]
    after = [(tt, p) for (tt, k, p) in events if k == "pos" and tt >= st]
    if not before or not after:
        continue
    last_pos = before[-1]
    (ft, fp) = after[0]
    d = ((fp[0]-last_pos[0])**2 + (fp[1]-last_pos[1])**2) ** 0.5
    wait = ft - st
    first_jump.append((idx+1, d, wait, last_pos, fp))
for n, d, wait, lp, fp in first_jump:
    flag = "  <-- JUMP" if d > 400 else ("  <-- notable" if d > 50 else "")
    print(f"start #{n}: first pos after {wait:.0f}ms, distance from pre-start pos = {d:.1f}px ({lp} -> {fp}){flag}")

# ── global mouse metrics over all positions ──────────────────────────────────
pos_events = [(tt, p) for (tt, k, p) in events if k == "pos"]
steps, gaps, teleports, stalls = [], [], [], []
for (t0, p0), (t1, p1) in zip(pos_events, pos_events[1:]):
    d = ((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2) ** 0.5
    dt = t1 - t0
    steps.append(d); gaps.append(dt)
    if d > 400 and dt < 100:
        teleports.append((t0/1000, p0, p1, d, dt))
    if dt >= 1000:
        stalls.append((t0/1000, dt/1000))
print("\n── movement metrics (all runs) ──")
print(f"moves: {len(steps)} · step median {statistics.median(steps):.2f}px · p90 {sorted(steps)[int(len(steps)*0.9)]:.1f}px · max {max(steps):.1f}px")
print(f"cadence median {statistics.median(gaps):.1f}ms")
print(f"teleports (>400px <100ms): {len(teleports)}")
for ts, p0, p1, d, dt in teleports[:12]:
    print(f"   t={ts:.1f}s  {p0} -> {p1}  {d:.0f}px in {dt:.0f}ms")
print(f"stalls >=1s between consecutive positions: {len(stalls)} (pauses/breaks are normal; shown for context)")

# ── where do teleports sit relative to Starts? ───────────────────────────────
if teleports:
    print("\n── teleport vs Start proximity ──")
    for ts, p0, p1, d, dt in teleports:
        prev_starts = [st for (st, _, _) in numlock_edges if st/1000 <= ts]
        if prev_starts:
            delta = ts - prev_starts[-1]/1000
            print(f"   t={ts:.1f}s is {delta:.2f}s after a Num Lock edge")
