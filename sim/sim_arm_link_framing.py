#!/usr/bin/env python3
"""sim_arm_link_framing.py - reproduce the 2026-09-10 hardware teleport in software,
then prove the v0.9.64c fix removes it.

Model:
  * plan_engine streams absolute MMOVE points 2-3 px apart every ~10 ms inside the
    region x=1301..1679 (the exported plan under test).
  * the pico<->arm UART drops a byte at a small rate; when the dropped byte is the
    leading '1' of x, the arm executes MMOVE|<x-1000>,y  (the field signature:
    1319,364 -> 319,364 / 1353,830 -> 353,830 / 1602,328 -> 602,328).
  * arm fw 2.3 plays any point > 60 px away as a paced sweep, so a corrupted point
    is a visible ~1000 px excursion and the next intact point snaps back.
  * with framing (arm fw >= 2.3 + pico v0.9.64c) a corrupted line fails the checksum
    and is DROPPED with ERR|CKSUM: the cursor never moves there.
"""
import random

REGION = (1301, 1679)
DROP_RATE = 0.004          # ~1 corrupted line per 250 (matches 3 events / ~800 points)


def frame(line):
    total = 0
    for b in line.encode():
        total = (total + b) & 0xFF
    return "#%02X|%s" % (total, line)


def unframe(line):
    """arm fw 2.3 frame_unwrap(): returns None when the line must be dropped."""
    if not line.startswith("#"):
        return line                      # legacy unframed: executed as-is
    if len(line) < 4 or line[3] != "|":
        return None
    want = int(line[1:3], 16)
    payload = line[4:]
    total = 0
    for b in payload.encode():
        total = (total + b) & 0xFF
    return payload if total == want else None


def corrupt(line):
    """drop the leading '1' of the x coordinate - the measured field failure."""
    head, _, args = line.partition("|")
    if head != "MMOVE" or not args.startswith("1"):
        return line
    return head + "|" + args[1:]


def path(rng, n=800):
    x, y = 1450, 500
    pts = []
    for _ in range(n):
        x = min(REGION[1], max(REGION[0], x + rng.randint(-3, 3)))
        y = min(1040, max(10, y + rng.randint(-3, 3)))
        pts.append((x, y))
    return pts


def run(framing, seed=7):
    rng = random.Random(seed)
    cur = (1450, 500)
    worst = 0
    excursions = 0
    dropped = 0
    for (x, y) in path(rng):
        wire = "MMOVE|%d,%d,abs,2" % (x, y)
        if framing:
            wire = frame(wire)
        if rng.random() < DROP_RATE:
            wire = corrupt(wire) if not framing else wire[:6] + wire[7:]
        payload = unframe(wire)
        if payload is None:
            dropped += 1
            continue                      # arm answers ERR|CKSUM, cursor does not move
        px, py = [int(v) for v in payload.split("|")[1].split(",")[:2]]
        jump = abs(px - cur[0])
        if jump > 300:
            excursions += 1
        worst = max(worst, jump)
        cur = (px, py)
    return worst, excursions, dropped


for seed in (7, 11, 23):
    w0, e0, d0 = run(False, seed)
    w1, e1, d1 = run(True, seed)
    print("seed %-3d  v0.9.64b unframed: worst jump %5d px, excursions %d" % (seed, w0, e0))
    print("          v0.9.64c framed  : worst jump %5d px, excursions %d, cksum drops %d" % (w1, e1, d1))
    assert e0 > 0, "the bug must reproduce without framing"
    assert e1 == 0 and w1 <= 10, "framing must remove every excursion"
print("PASS: teleport reproduced without framing, zero excursions with framing")
