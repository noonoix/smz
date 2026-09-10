#!/usr/bin/env python3
# Classroom Studio - patch_arm_diag_0964f.py
#
# code64b.py v0.9.64e -> v0.9.64f
#
# What the 0.9.64e run proved (log 08:58:44 + recorder 09:01):
#   * 6x 'SENT JUMP' fired, but ALL of them stayed inside the plan region
#     (x 1406-1612, y 126-1005) and every one of them landed next to a coalesce
#     event -> they are the expected gap left by dropped mid-path points, not a bug.
#   * The ONE real teleport in the recorder (t=13770, (305,458) -> (1651,82),
#     d=1398) had NO 'SENT JUMP' anywhere near it, and the run logged ZERO
#     CKSUM and ZERO NOFRAME drops.
#
# So the corrupted target was never seen by the 0.9.64e telemetry. Two blind spots
# explain that, and this build closes both:
#
#   1. Coverage. The 0.9.64e check sat inside forward_fast, AFTER the coalesce
#      branch returns, so the '_pending_move' flush inside pump_arm (which calls
#      _arm_write directly) was never inspected. The check now lives in _arm_write
#      itself - the single place every byte leaves the Pico.
#   2. Short UART writes. busio.UART.write() can write fewer bytes than asked.
#      0.9.64e ignored the return value, so a truncated frame would be spliced with
#      the next line on the arm - and the checksum, computed BEFORE the truncation,
#      cannot catch it. Short writes are now counted and printed.
#
# Also: jumps that follow a coalesce drop are tagged 'after-drop' (expected) and
# jumps with no drop in between are tagged 'NO-DROP' (a real Pico-side bug).
#
# Usage: python3 patch_arm_diag_0964f.py code64b.py [-o out.py]

import argparse, hashlib, sys

NOTE_SENT = '''def _note_sent(line):
    """v0.9.64f - sent-stream watchdog on the ONE place every line is written.
    A gap right after a coalesce drop is expected (the dropped mid-points ARE the
    gap and the arm interpolates across them), so those are tagged 'after-drop'.
    A jump with no drop in between is a genuine Pico-side bug and says NO-DROP."""
    global _last_sent_xy, _sent_jumps, _drops_at_last_send
    if not line.startswith("MMOVE|"):
        return
    try:
        _p = line.split("|")[1].split(",")
        nx = int(_p[0])
        ny = int(_p[1])
    except Exception:
        return
    prev = _last_sent_xy
    coalesced = _moves_dropped != _drops_at_last_send
    _last_sent_xy = (nx, ny)
    _drops_at_last_send = _moves_dropped
    if prev is None:
        return
    dx = nx - prev[0]
    dy = ny - prev[1]
    if dx * dx + dy * dy <= MOVE_JUMP_PX * MOVE_JUMP_PX:
        return
    _sent_jumps += 1
    print("plan: SENT JUMP #%d %s -> %d,%d (dx=%d dy=%d) %s" % (
        _sent_jumps, prev, nx, ny, dx, dy,
        "after-drop" if coalesced else "NO-DROP"))


'''

EDITS = [
    (
        "header",
        "# Classroom Studio v0.9.64e",
        "# Classroom Studio v0.9.64f",
    ),
    (
        "diag state",
        "_last_sent_xy = None  # v0.9.64e - previous MMOVE target actually written to the arm\n"
        "_sent_jumps = 0       # v0.9.64e - jumps in the SENT stream (a Pico-side bug, not the wire)\n"
        "MOVE_JUMP_PX = 200    # v0.9.64e - a humanized path step is 2-3 px; 200 px is never legitimate",
        "_last_sent_xy = None  # v0.9.64e - previous MMOVE target actually written to the arm\n"
        "_sent_jumps = 0       # v0.9.64e - jumps in the SENT stream (a Pico-side bug, not the wire)\n"
        "_drops_at_last_send = 0  # v0.9.64f - coalesce counter at the previous write (gap = expected)\n"
        "_partial_writes = 0   # v0.9.64f - short UART writes: a truncated frame the checksum cannot catch\n"
        "MOVE_JUMP_PX = 200    # v0.9.64e - a humanized path step is 2-3 px; 200 px is never legitimate",
    ),
    (
        "note_sent + write guard",
        "def _arm_write(line):\n"
        "    if arm is None:\n"
        "        return False\n"
        "    try:\n"
        "        out = _frame(line) if ARM_FRAMING else line     # v0.9.64c\n"
        '        arm.write((out + "\\n").encode("utf-8"))\n'
        "        return True\n"
        "    except Exception:\n"
        "        return False",
        NOTE_SENT +
        "def _arm_write(line):\n"
        "    global _partial_writes\n"
        "    if arm is None:\n"
        "        return False\n"
        "    try:\n"
        "        out = _frame(line) if ARM_FRAMING else line     # v0.9.64c\n"
        '        buf = (out + "\\n").encode("utf-8")\n'
        "        n = arm.write(buf)\n"
        "        if n is not None and n != len(buf):\n"
        "            # v0.9.64f - a short write truncates the frame mid-line and the arm\n"
        "            # splices the remnant onto the next one. The checksum is computed\n"
        "            # before the truncation, so it cannot catch this.\n"
        "            _partial_writes += 1\n"
        '            print("arm: PARTIAL WRITE #%d (%d of %d bytes)" % (_partial_writes, n, len(buf)))\n'
        "        _note_sent(line)      # v0.9.64f - covers EVERY write path, flush included\n"
        "        return True\n"
        "    except Exception:\n"
        "        return False",
    ),
    (
        "drop the 0.9.64e inline check",
        "        # v0.9.64e - telemetry only: does the Pico itself ever emit a jump? A\n"
        "        # humanized path moves 2-3 px per point, so anything over MOVE_JUMP_PX in\n"
        "        # the SENT stream is a Pico-side bug, and its absence proves the wire.\n"
        "        try:\n"
        '            _xy = line.split("|")[1].split(",")\n'
        "            _nx = int(_xy[0])\n"
        "            _ny = int(_xy[1])\n"
        "            if _last_sent_xy is not None:\n"
        "                _dx = _nx - _last_sent_xy[0]\n"
        "                _dy = _ny - _last_sent_xy[1]\n"
        "                if _dx * _dx + _dy * _dy > MOVE_JUMP_PX * MOVE_JUMP_PX:\n"
        "                    _sent_jumps += 1\n"
        '                    print("plan: SENT JUMP #%d %s -> %d,%d (dx=%d dy=%d)" % (\n'
        "                        _sent_jumps, _last_sent_xy, _nx, _ny, _dx, _dy))\n"
        "            _last_sent_xy = (_nx, _ny)\n"
        "        except Exception:\n"
        "            pass\n"
        "        if _arm_write(line):",
        "        if _arm_write(line):",
    ),
    (
        "forward_fast globals",
        "    global _arm_lag, _pending_move, _moves_dropped\n"
        "    global _last_sent_xy, _sent_jumps      # v0.9.64e - sent-stream telemetry",
        "    global _arm_lag, _pending_move, _moves_dropped",
    ),
    (
        "ping",
        'return "OK|PONG|pico-light 0.9.64e|role=brain+keyboard+light|arm=promicro|framing=%d|baud=%d|lagmax=%d|dropped=%d|cksum=%d|noframe=%d|sentjumps=%d" % (1 if ARM_FRAMING else 0, ARM_BAUD, ARM_LAG_MAX, _moves_dropped, _cksum_errors, _noframe_errors, _sent_jumps)',
        'return "OK|PONG|pico-light 0.9.64f|role=brain+keyboard+light|arm=promicro|framing=%d|baud=%d|lagmax=%d|dropped=%d|cksum=%d|noframe=%d|sentjumps=%d|partial=%d" % (1 if ARM_FRAMING else 0, ARM_BAUD, ARM_LAG_MAX, _moves_dropped, _cksum_errors, _noframe_errors, _sent_jumps, _partial_writes)',
    ),
    (
        "boot banner",
        'print("pico-light 0.9.64e | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause | arm framing=%s baud=%d lagmax=%d | diag=on" % (ARM_FRAMING, ARM_BAUD, ARM_LAG_MAX))',
        'print("pico-light 0.9.64f | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause | arm framing=%s baud=%d lagmax=%d | diag=full" % (ARM_FRAMING, ARM_BAUD, ARM_LAG_MAX))',
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    out = open(a.path, encoding="utf-8").read()
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            print("FAIL: anchor %r found %d times (expected 1)" % (name, n))
            return 1
        out = out.replace(old, new, 1)

    checks = [
        (out.count("        _note_sent(line)") != 1, "_note_sent is not called exactly once"),
        ("def _note_sent" not in out, "_note_sent helper missing"),
        (out.index("def _note_sent") > out.index("def _arm_write"),
         "_note_sent defined after _arm_write"),
        ("_partial_writes += 1" not in out, "short-write detection missing"),
        ("ARM_LAG_MAX = 2" not in out, "0.9.64d back-pressure was lost"),
        (out.index("ARM_BAUD = 57600") > out.index("baudrate=ARM_BAUD"),
         "ARM_BAUD defined after the UART init: NameError -> arm=None -> dead mouse"),
        (out.index("_drops_at_last_send = 0") > out.index("def _note_sent"),
         "_drops_at_last_send used before it is defined"),
        ("_noframe_errors += 1" not in out, "NOFRAME counter was lost"),
        ("pico-light 0.9.64e" in out, "a live 0.9.64e version string survived"),
    ]
    for bad, msg in checks:
        if bad:
            print("FAIL: " + msg)
            return 1

    dest = a.out or a.path
    open(dest, "w", encoding="utf-8").write(out)
    print("PASS: %d edits applied -> %s" % (len(EDITS), dest))
    print("bytes  : %d" % len(out.encode("utf-8")))
    print("sha256 : %s" % hashlib.sha256(out.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
