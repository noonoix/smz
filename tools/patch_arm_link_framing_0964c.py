#!/usr/bin/env python3
"""patch_arm_link_framing_0964c.py - Classroom Studio v0.9.64b -> v0.9.64c

Fixes the plan-mode cursor teleport measured on hardware 2026-09-10.

Field evidence (32 s plan pass, 2081 recorder samples, region x=1301..1679):
  target 1319,364 -> landed  319,364
  target 1353,830 -> landed  353,830
  target 1602,328 -> landed  602,328
Every excursion is the correct target with the LEADING '1' of x missing: the
unframed pico<->arm UART dropped a byte, the arm executed the corrupted MMOVE,
swept ~1280 px left, and the next intact MMOVE snapped the cursor back right.
Arm fw 2.3 already ships the cure (checksum frames, ERR|CKSUM) but the Pico
never used it.

What this patch changes in firmware/code64b/code64b.py (Pico side only):
  1. _arm_write() wraps every arm line as '#' + 2 hex (sum of payload bytes
     mod 256) + '|' + payload  -> a corrupted line is DROPPED by the arm,
     never executed. ARM_FRAMING=False restores fw<=2.2 behaviour.
  2. pump_arm() counts ERR|CKSUM drops, prints them, and decrements the lag
     ledger (the dropped line will never be acked).
  3. The ack watchdog DISCARDS the stale coalesced target instead of flushing
     it - flushing a hundreds-of-px-old absolute target is the catch-up dart.
  4. Version strings -> 0.9.64c.

Usage:  python3 tools/patch_arm_link_framing_0964c.py firmware/code64b/code64b.py
Idempotent check: refuses to patch a file that already says 0.9.64c.
"""
import argparse
import hashlib
import sys

EDITS = []


def edit(name, old, new):
    EDITS.append((name, old, new))


# ---- 1. header ------------------------------------------------------------
edit(
    "header-version",
    "# Classroom Studio v0.9.64b - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)",
    "# Classroom Studio v0.9.64c - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)",
)

# ---- 2. constants ---------------------------------------------------------
edit(
    "framing-consts",
    'ARM_ACK_TIMEOUT = 1.0  # v0.9.62 - lag this old with zero acks = the ledger drifted: self-heal\n',
    'ARM_ACK_TIMEOUT = 1.0  # v0.9.62 - lag this old with zero acks = the ledger drifted: self-heal\n'
    '\n'
    '# v0.9.64c - arm-link integrity frames (needs arm fw >= 2.3). Every line written to the\n'
    '# Pro Micro is wrapped as \'#\' + 2 hex (sum of the payload bytes mod 256) + \'|\' + payload.\n'
    '# The unframed UART drops bytes in the field: 2026-09-10 hardware run, three ~1280 px\n'
    '# out-and-back teleports in one 32 s plan pass, each landing exactly on the target minus\n'
    '# the leading \'1\' of x (MMOVE|1319,364 executed as 319,364). A framed line whose sum does\n'
    '# not match is dropped by the arm with ERR|CKSUM and NEVER executed - and a dropped path\n'
    '# point is invisible, because the next point of the humanized path is 2-3 px away.\n'
    'ARM_FRAMING = True     # set False only for an arm running fw <= 2.2\n'
    '_cksum_errors = 0      # v0.9.64c - corrupted lines the arm rejected since boot\n',
)

# ---- 3. _arm_write --------------------------------------------------------
edit(
    "arm-write-framing",
    'def _arm_write(line):\n'
    '    if arm is None:\n'
    '        return False\n'
    '    try:\n'
    '        arm.write((line + "\\n").encode("utf-8"))\n'
    '        return True\n'
    '    except Exception:\n'
    '        return False\n',
    'def _frame(line):\n'
    '    """v0.9.64c - arm fw>=2.3 integrity frame: \'#\' + 2 hex byte-sum + \'|\' + payload."""\n'
    '    total = 0\n'
    '    for b in line.encode("utf-8"):\n'
    '        total = (total + b) & 0xFF\n'
    '    return "#%02X|%s" % (total, line)\n'
    '\n'
    '\n'
    'def _arm_write(line):\n'
    '    if arm is None:\n'
    '        return False\n'
    '    try:\n'
    '        out = _frame(line) if ARM_FRAMING else line     # v0.9.64c\n'
    '        arm.write((out + "\\n").encode("utf-8"))\n'
    '        return True\n'
    '    except Exception:\n'
    '        return False\n',
)

# ---- 4. pump_arm: globals + CKSUM accounting ------------------------------
edit(
    "pump-globals",
    '    global _arm_buf, _arm_lag, _pending_move, _arm_last_ack   # 60c: slice-safe flow; 62: watchdog\n',
    '    global _arm_buf, _arm_lag, _pending_move, _arm_last_ack, _cksum_errors   # 60c: flow; 62: watchdog; 64c: cksum\n',
)

edit(
    "cksum-counter",
    '        if line.startswith("EVT|"):\n'
    '            _serial_write_line(line)              # arm events reach the PC live\n'
    '            continue\n',
    '        if line.startswith("EVT|"):\n'
    '            _serial_write_line(line)              # arm events reach the PC live\n'
    '            continue\n'
    '        if line.startswith("ERR|CKSUM"):\n'
    '            # v0.9.64c - the arm caught a corrupted line and refused to execute it.\n'
    '            # It will never be acked, so the lag ledger must be settled here, and the\n'
    '            # drop is printed: a rising counter = a wiring/baud problem, not a bug.\n'
    '            _cksum_errors += 1\n'
    '            if _arm_lag > 0:\n'
    '                _arm_lag -= 1\n'
    '            print("arm: CKSUM drop #%d (line rejected, not executed)" % _cksum_errors)\n'
    '            continue\n',
)

# ---- 5. watchdog: discard instead of flush --------------------------------
edit(
    "watchdog-discard",
    '    if _arm_lag > 0 and time.monotonic() - _arm_last_ack > ARM_ACK_TIMEOUT:\n'
    '        print("arm: ack watchdog reset (lag was %d)" % _arm_lag)\n'
    '        _arm_lag = 0\n'
    '        if _pending_move is not None:\n'
    '            if engine_on and not engine_paused and _arm_write(_pending_move):\n'
    '                _arm_lag = 1\n'
    '            _pending_move = None\n',
    '    if _arm_lag > 0 and time.monotonic() - _arm_last_ack > ARM_ACK_TIMEOUT:\n'
    '        print("arm: ack watchdog reset (lag was %d)" % _arm_lag)\n'
    '        _arm_lag = 0\n'
    '        _arm_last_ack = time.monotonic()   # v0.9.64c - no immediate re-trigger\n'
    '        if _pending_move is not None:\n'
    '            # v0.9.64c - DISCARD the stale coalesced target, never flush it. By the time\n'
    '            # the watchdog fires the target is up to a second old (hundreds of px behind\n'
    '            # the live path) and replaying it is exactly the catch-up dart seen on\n'
    '            # hardware. The plan engine sends the next path point ~10 ms later, 2-3 px\n'
    '            # from the cursor, so dropping it costs nothing.\n'
    '            _pending_move = None\n',
)

# ---- 6. version strings ---------------------------------------------------
edit(
    "ping-banner",
    'return "OK|PONG|pico-light 0.9.64b|role=brain+keyboard+light|arm=promicro"',
    'return "OK|PONG|pico-light 0.9.64c|role=brain+keyboard+light|arm=promicro|framing=%d" % (1 if ARM_FRAMING else 0)',
)

edit(
    "boot-banner",
    'print("pico-light 0.9.64b | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause")',
    'print("pico-light 0.9.64c | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause | arm framing=%s" % ARM_FRAMING)',
)


def apply(text):
    for name, old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit("FAIL: anchor '%s' found %d times (expected 1)" % (name, n))
        text = text.replace(old, new)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    with open(a.src, "r", encoding="utf-8") as fh:
        text = fh.read()
    if "0.9.64c" in text:
        raise SystemExit("FAIL: source already patched to 0.9.64c")
    out_text = apply(text)
    dst = a.out or a.src
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out_text)
    checks = [
        ("ARM_FRAMING = True" in out_text, "ARM_FRAMING constant"),
        ("def _frame(line):" in out_text, "_frame helper"),
        ('out = _frame(line) if ARM_FRAMING else line' in out_text, "framed write"),
        ('ERR|CKSUM' in out_text, "cksum accounting"),
        ('if engine_on and not engine_paused and _arm_write(_pending_move):' not in out_text,
         "watchdog no longer flushes the stale target"),
    ]
    bad = [msg for ok, msg in checks if not ok]
    if bad:
        raise SystemExit("FAIL: " + ", ".join(bad))
    sha = hashlib.sha256(out_text.encode("utf-8")).hexdigest()
    print("PASS: %d edits applied -> %s" % (len(EDITS), dst))
    print("PASS: framing on, cksum accounting on, watchdog discards stale target")
    print("sha256 %s" % sha)
    print("bytes  %d" % len(out_text.encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
