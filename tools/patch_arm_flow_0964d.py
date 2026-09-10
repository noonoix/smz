#!/usr/bin/env python3
# Classroom Studio - patch_arm_flow_0964d.py
#
# firmware/code64b/code64b.py v0.9.64c -> v0.9.64d
#
# Why: v0.9.64c added integrity frames, but the hardware re-test still teleported
# ~1000 px left three times in 58 s (recorder trace: 1349->349, 1263->263,
# 1221->221 in x). Measured cause: the Pro Micro's 64-byte Serial1 RX buffer
# overflows while the arm blocks inside mouse_move_stream() (20..160 ms of
# delay() per point, while the Pico feeds a point every ~10 ms). The overflow
# eats a multi-byte CHUNK, which can swallow the '#XX|' frame header of the
# following line; arm fw 2.3 passes header-less lines through unchecked, so a
# truncated "MMOVE|349,520" executes and drags the cursor 1000 px left.
#
# 0.9.64d removes the overflow itself and slows the link:
#   * ARM_LAG_MAX 8 -> 2 (2 unacked MMOVEs ~= 52 bytes, under the 64-byte buffer)
#   * dense path points are dropped, not queued (the arm interpolates 3 px steps)
#   * internal UART 115200 -> 57600 (edge margin on the BSS138 shifter)
#
# Pair with arm fw 2.4 (tools/patch_arm_fw24.py), which refuses header-less lines.
#
# Usage: python3 patch_arm_flow_0964d.py code64b.py [-o out.py]

import argparse, hashlib, sys

EDITS = [
    (
        "header",
        "# Classroom Studio v0.9.64c",
        "# Classroom Studio v0.9.64d",
    ),
    (
        "uart baud",
        "    arm = busio.UART(board.GP16, board.GP17, baudrate=115200, timeout=0.2)",
        "    arm = busio.UART(board.GP16, board.GP17, baudrate=ARM_BAUD, timeout=0.2)",
    ),
    (
        "lag cap + drop counter",
        "ARM_LAG_MAX = 8       # v0.9.60c - coalesce dense mouse moves once the arm is this far behind",
        "ARM_LAG_MAX = 2       # v0.9.64d - real back-pressure. 8 unacked MMOVEs are ~220 bytes and\n"
        "                      # the Pro Micro's Serial1 RX buffer is 64 bytes: the overflow ate a\n"
        "                      # multi-byte chunk (sometimes a whole '#XX|' frame header) and fw 2.3\n"
        "                      # executed the header-less remnant as a bare MMOVE -> 1000 px teleport.\n"
        "                      # 2 in flight = ~52 bytes, always under the buffer.\n"
        "_moves_dropped = 0    # v0.9.64d - path points skipped because the arm was busy",
    ),
    (
        "framing note + baud",
        "ARM_FRAMING = True     # set False only for an arm running fw <= 2.2",
        "ARM_FRAMING = True     # set False only for an arm running fw <= 2.2\n"
        "ARM_BAUD = 57600       # v0.9.64d - must match Serial1.begin() in the arm sketch (fw >= 2.4)",
    ),
    (
        "drop instead of queue",
        "        if _arm_lag >= ARM_LAG_MAX:\n"
        "            _pending_move = line          # absolute move: the newest target wins\n"
        "            return None                   # no per-move ack (send_path never reads them)",
        "        if _arm_lag >= ARM_LAG_MAX:\n"
        "            # v0.9.64d - the arm is busy: keep ONLY the newest target and never write.\n"
        "            # Queueing more bytes is what overflowed the arm's 64-byte RX buffer; the\n"
        "            # arm interpolates in 3 px micro-steps, so a skipped mid-path point is invisible.\n"
        "            _moves_dropped += 1\n"
        "            _pending_move = line          # absolute move: the newest target wins\n"
        "            return None                   # no per-move ack (send_path never reads them)",
    ),
    (
        "forward_fast globals",
        "    global _arm_lag, _pending_move\n"
        "    head = line.split(\"|\")[0]",
        "    global _arm_lag, _pending_move, _moves_dropped\n"
        "    head = line.split(\"|\")[0]",
    ),
    (
        "ping",
        'return "OK|PONG|pico-light 0.9.64c|role=brain+keyboard+light|arm=promicro|framing=%d" % (1 if ARM_FRAMING else 0)',
        'return "OK|PONG|pico-light 0.9.64d|role=brain+keyboard+light|arm=promicro|framing=%d|baud=%d|lagmax=%d|dropped=%d" % (1 if ARM_FRAMING else 0, ARM_BAUD, ARM_LAG_MAX, _moves_dropped)',
    ),
    (
        "boot banner",
        'print("pico-light 0.9.64c | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause | arm framing=%s" % ARM_FRAMING)',
        'print("pico-light 0.9.64d | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause | arm framing=%s baud=%d lagmax=%d" % (ARM_FRAMING, ARM_BAUD, ARM_LAG_MAX))',
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = open(a.path, encoding="utf-8").read()
    out = src
    applied = 0
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            print("FAIL: anchor %r found %d times (expected 1)" % (name, n))
            return 1
        out = out.replace(old, new, 1)
        applied += 1

    checks = [
        ("ARM_LAG_MAX = 2" not in out, "lag cap not lowered to 2"),
        ("ARM_BAUD = 57600" not in out, "link baud constant missing"),
        ("baudrate=ARM_BAUD" not in out, "UART still hard-coded to 115200"),
        ("_moves_dropped += 1" not in out, "drop counter never increments"),
        # historical changelog comments keep saying 0.9.64c on purpose; only the
        # three live version strings (header, PING, banner) must move to 0.9.64d
        ("# Classroom Studio v0.9.64c" in out, "header still says 0.9.64c"),
        ("pico-light 0.9.64c" in out, "a live 0.9.64c version string survived"),
        ("if engine_on and not engine_paused and _arm_write(_pending_move):" in out,
         "the 0.9.64c watchdog fix was reverted (stale target would flush again)"),
    ]
    for bad, msg in checks:
        if bad:
            print("FAIL: " + msg)
            return 1

    dest = a.out or a.path
    open(dest, "w", encoding="utf-8").write(out)
    print("PASS: %d edits applied -> %s" % (applied, dest))
    print("bytes  : %d" % len(out.encode("utf-8")))
    print("sha256 : %s" % hashlib.sha256(out.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
