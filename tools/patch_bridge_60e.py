# patch_bridge_60e.py - patch the release's bridge.py in place.
# Variant-aware + per-edit idempotent: understands a CLEAN bridge.py, a v1-patched one
# (stale-skip + drain + KTEXT timeout), a v2 one (adds the MMOVE local-ack), and a full
# v3 one - and applies only the missing deltas. Safe to re-run any number of times.
#
# ROOT CAUSES (hardware logs 2026-09-08):
#  A) reply mis-pairing (runs of 16:53-16:55): PicoLink.command() returned the FIRST
#     non-EVT line on the wire - including stale answers owed to write-only abort HALTs
#     and late PONGs from send_path's drain pings (the user's log: SETRES <- OK|HALT,
#     then SETRES <- OK|PONG on every repeat) - and left the pipe dirty for the next
#     run (the 17:13 playScript hang).
#  B) choppy mouse (runs of 20:14-20:16): the arm executes ~50 moves/sec (HID frame +
#     UART + pico loop = ~20 ms per move; the logs measure 19-22 ms/step). Dense
#     WindMouse trails arrive at ~4 ms/point = 4-5x oversubscribed, so the firmware's
#     coalescing dropped intermediate points -> visible jumps ("choppy"). Fix: merge
#     micro-steps so every emitted point gets >= 25 ms - same total time, same curve,
#     and every point actually executes.
#
# Fixes (ASCII anchors only - safe against code-page mangling of the Persian comments):
#  1) PicoLink.command: skip stale replies - OK|X / ERR|?|X whose X is not this
#     command's head are eaten (PING's answer is PONG). Real ERRs pass through.
#  2) worker: drain the pipe before each send / send_path (zero cost when quiet).
#  3) KTEXT gets a payload-sized timeout (len x hmax + margin) - humanized typing of a
#     long text legitimately takes minutes; the flat 5 s default killed it.
#  4) a lone MMOVE sent as a "send" op is acked locally: firmware 60c made MMOVE
#     fire-and-forget (no reply ever comes), so it would wait 5 s and die (latent 60c
#     regression hit by single moves: findImage approach, parallel-group waypoints).
#  5) send_path hardware-cadence thinning (the choppy-mouse fix, ~25 ms/point).
#  6) one retry on ERR|UNKNOWN: a UART-garbled command is never executed by the board
#     (ERR|UNKNOWN is only answered to unrecognized lines), so resending once is always
#     safe (hardware log 2026-09-09: SETRES <- ERR|UNKNOWN once in ~25 repeats).
#  7) send_path streams points as MMOVE abs,2: arm fw 1.9 subdivides each fed segment
#     into <=8 px micro-steps at native HID pace -> hand-smooth (~100 reports/sec; the
#     user's own hand recording measures ~3 px steps at ~390 samples/sec, ~530 px/s
#     median). Older arm firmware reads hm==2 as a plain per-point jump - graceful.
#
# Usage:  python patch_bridge_60e.py "C:\...\ClassroomStudio\bridge\bridge.py"
import shutil
import sys

# -- shared text blocks --

HELPERS = (
    "def _drain_stale(link):\n"
    "    \"\"\"v0.9.60e - eat stale PicoLink lines (write-only abort HALT answers, late\n"
    "    PONGs) before a new op pairs them with its own reply. Zero cost on a quiet pipe.\n"
    "    BoardLink (encrypted, direct arm) already resyncs - left untouched.\"\"\"\n"
    "    if not isinstance(link, PicoLink):\n"
    "        return\n"
    "    try:\n"
    "        ser = getattr(link, \"ser\", None)\n"
    "        if ser is None or (not getattr(ser, \"in_waiting\", 0) and not getattr(link, \"_rxbuf\", None)):\n"
    "            return\n"
    "        while True:\n"
    "            line = link._read_line(0.1)\n"
    "            if line is None:\n"
    "                return\n"
    "            if line.startswith(\"EVT|\"):\n"
    "                link.events.append(line)\n"
    "    except Exception:\n"
    "        return\n"
    "\n\n"
    "def _ktext_timeout(cmd, default):\n"
    "    \"\"\"v0.9.60e - humanized typing is deliberately slow: size the wait from the\n"
    "    payload (len x hmax + margin) so a long Type Text never dies at 5 s.\"\"\"\n"
    "    inner = cmd\n"
    "    for env in (\"KBDPICO|\", \"KBDARM|\"):\n"
    "        if inner.startswith(env):\n"
    "            inner = inner[len(env):]\n"
    "    if not inner.startswith(\"KTEXT|\"):\n"
    "        return default\n"
    "    try:\n"
    "        p = inner[6:].split(\",\", 2)\n"
    "        per_ms = max(int(p[0]), int(p[1]))\n"
    "        return max(default, 5.0 + len(p[2]) * per_ms / 1000.0 + 5.0)\n"
    "    except Exception:\n"
    "        return default\n"
    "\n\n"
)

# edit 3 (send op) - three known states
SEND_CLEAN_OLD = (
    "                    cmd = req[\"cmd\"]\n"
    "                    abort_flag.clear()\n"
    "                    reply = link.command(cmd, timeout=req.get(\"timeout\", 5.0))\n"
)
SEND_V1_OLD = (   # v1-patched: drain present, KTEXT timeout present, NO MMOVE ack
    "                    _drain_stale(link)         # v0.9.60e - eat leftovers of write-only aborts\n"
    "                    reply = link.command(cmd, timeout=_ktext_timeout(cmd, req.get(\"timeout\", 5.0)))\n"
)
SEND_V1_NEW = (   # insert only the MMOVE-ack delta
    "                    _drain_stale(link)         # v0.9.60e - eat leftovers of write-only aborts\n"
    "                    if cmd.split(\"|\", 1)[0] == \"MMOVE\":\n"
    "                        # v0.9.60e - firmware 60c made MMOVE fire-and-forget (no reply is\n"
    "                        # ever sent): a lone MMOVE via a \"send\" op would wait 5 s and die.\n"
    "                        link._send(cmd)\n"
    "                        reply = \"OK|MMOVE\"      # local ack, same contract as send_path\n"
    "                    else:\n"
    "                        reply = link.command(cmd, timeout=_ktext_timeout(cmd, req.get(\"timeout\", 5.0)))\n"
)
SEND_FULL_NEW = (   # clean -> v3 in one go
    "                    cmd = req[\"cmd\"]\n"
    "                    abort_flag.clear()\n"
    "                    _drain_stale(link)         # v0.9.60e - eat leftovers of write-only aborts\n"
    "                    if cmd.split(\"|\", 1)[0] == \"MMOVE\":\n"
    "                        # v0.9.60e - firmware 60c made MMOVE fire-and-forget (no reply is\n"
    "                        # ever sent): a lone MMOVE via a \"send\" op would wait 5 s and die.\n"
    "                        link._send(cmd)\n"
    "                        reply = \"OK|MMOVE\"      # local ack, same contract as send_path\n"
    "                    else:\n"
    "                        reply = link.command(cmd, timeout=_ktext_timeout(cmd, req.get(\"timeout\", 5.0)))\n"
)

# edit 4 (send_path) - three known states
PATH_CLEAN_OLD = (
    "                    aborted = False\n"
    "                    t0 = time.monotonic()\n"
)
PATH_V1V2_OLD = (   # v1/v2-patched: drain line present, NO thinning
    "                    _drain_stale(link)         # v0.9.60e - clean pipe before streaming\n"
    "                    aborted = False\n"
    "                    t0 = time.monotonic()\n"
)
THINNING = (
    "                    # v0.9.60f - hardware-cadence thinning (the choppy-mouse fix). The arm\n"
    "                    # executes ~50 moves/sec (~20 ms each, measured 2026-09-08), but dense\n"
    "                    # WindMouse trails arrive at ~4 ms/point: oversubscribed 4-5x, the\n"
    "                    # firmware's coalescing dropped points and the cursor visibly jumped.\n"
    "                    # Merge micro-steps so every emitted point gets >= MIN_STEP_MS: same\n"
    "                    # total time, same curve shape, and every point actually executes.\n"
    "                    MIN_STEP_MS = 25\n"
    "                    if len(pts) > 1 and dlys:\n"
    "                        tp, td = [pts[0]], []\n"
    "                        acc = 0\n"
    "                        for i in range(1, len(pts)):\n"
    "                            acc += dlys[i - 1] if i - 1 < len(dlys) else 0\n"
    "                            if acc >= MIN_STEP_MS:\n"
    "                                tp.append(pts[i])\n"
    "                                td.append(acc)\n"
    "                                acc = 0\n"
    "                        if tp[-1] != pts[-1]:\n"
    "                            tp.append(pts[-1])     # the final target ALWAYS lands\n"
    "                            td.append(acc)\n"
    "                        pts, dlys = tp, td\n"
)
PATH_V1V2_NEW = (   # insert only the thinning delta after the existing drain line
    "                    _drain_stale(link)         # v0.9.60e - clean pipe before streaming\n"
    + THINNING +
    "                    aborted = False\n"
    "                    t0 = time.monotonic()\n"
)
PATH_FULL_NEW = (   # clean -> v3 in one go
    "                    _drain_stale(link)         # v0.9.60e - clean pipe before streaming\n"
    + THINNING +
    "                    aborted = False\n"
    "                    t0 = time.monotonic()\n"
)

# (idempotency marker, [(old, new) variants ordered most-patched -> cleanest])
EDITS = [
    # 1a) compute the expected reply head before the read loop
    ("want = \"PONG\" if expect == \"PING\" else expect",
     [("        self._send(cmd)\n"
       "        deadline = time.monotonic() + timeout\n"
       "        while True:\n",
       "        self._send(cmd)\n"
       "        deadline = time.monotonic() + timeout\n"
       "        # v0.9.60e - never mis-pair a stale reply with this command: a write-only\n"
       "        # abort HALT answer or a late PONG used to be returned as the NEXT command's\n"
       "        # reply (hardware log: SETRES <- OK|HALT / OK|PONG). Skip OK|X / ERR|?|X\n"
       "        # whose X is not this command's head (PING's answer is PONG).\n"
       "        expect = cmd.split(\"|\")[0]\n"
       "        if expect in (\"KBDPICO\", \"KBDARM\") and \"|\" in cmd:\n"
       "            expect = cmd.split(\"|\", 2)[1]\n"
       "        want = \"PONG\" if expect == \"PING\" else expect\n"
       "        while True:\n")]),
    # 1b) the stale skip right before the reply is returned
    ("stale ERR of an older command",
     [("                continue\n"
       "            return line\n",
       "                continue\n"
       "            parts = line.split(\"|\")\n"
       "            if len(parts) >= 2 and parts[0] == \"OK\" and parts[1] and parts[1] != want:\n"
       "                continue                 # v0.9.60e - stale OK of an older command\n"
       "            if len(parts) >= 3 and parts[0] == \"ERR\" and parts[2] and parts[2] != expect:\n"
       "                continue                 # v0.9.60e - stale ERR of an older command\n"
       "            return line\n")]),
    # 2) the two helpers, right before open_link
    ("def _ktext_timeout(cmd, default):",
     [("def open_link(port):\n",
       HELPERS + "def open_link(port):\n")]),
    # 3) send op: drain + MMOVE local-ack + sized KTEXT timeout
    ("reply = \"OK|MMOVE\"",
     [(SEND_V1_OLD, SEND_V1_NEW),        # v1-patched -> v3 (delta only)
      (SEND_CLEAN_OLD, SEND_FULL_NEW)]), # clean -> v3
    # 4) send_path: drain + hardware-cadence thinning
    ("MIN_STEP_MS = 25",
     [(PATH_V1V2_OLD, PATH_V1V2_NEW),        # v1/v2-patched -> v3 (delta only)
      (PATH_CLEAN_OLD, PATH_FULL_NEW)]),     # clean -> v3
    # 5) one-shot retry flag for the ERR|UNKNOWN retry (lives in command()'s frame)
    ("retried = False",
     [("        want = \"PONG\" if expect == \"PING\" else expect\n        while True:\n",
       "        want = \"PONG\" if expect == \"PING\" else expect\n"
       "        retried = False                  # v0.9.60g - one retry on ERR|UNKNOWN (UART glitch)\n"
       "        while True:\n")]),
    # 6) retry-on-UNKNOWN right before the reply is returned (post-1b text)
    ('if line == "ERR|UNKNOWN" and not retried:',
     [("            if len(parts) >= 3 and parts[0] == \"ERR\" and parts[2] and parts[2] != expect:\n"
       "                continue                 # v0.9.60e - stale ERR of an older command\n"
       "            return line\n",
       "            if len(parts) >= 3 and parts[0] == \"ERR\" and parts[2] and parts[2] != expect:\n"
       "                continue                 # v0.9.60e - stale ERR of an older command\n"
       "            if line == \"ERR|UNKNOWN\" and not retried:\n"
       "                # v0.9.60g - UART noise garbled that command; the board answers\n"
       "                # ERR|UNKNOWN only for lines it did NOT execute -> one resend is safe.\n"
       "                retried = True\n"
       "                self._send(cmd)\n"
       "                deadline = time.monotonic() + timeout\n"
       "                continue\n"
       "            return line\n")]),
    # 7) stream path points as abs,2 (arm fw 1.9 interpolates; older arms degrade to jumps)
    ('",abs,2"',
     [("                        send(\"MMOVE|\" + p + \",abs,0\")\n",
       "                        # v0.9.60g - abs,2 = interpolated path point (arm fw 1.9 splits each\n"
       "                        # segment into <=8 px native-paced micro-steps -> hand-smooth). An\n"
       "                        # older arm reads hm==2 as non-human and jumps per point (the v3.1\n"
       "                        # behaviour) - safe either way; flash fw 1.9 for the smoothness.\n"
       "                        send(\"MMOVE|\" + p + \",abs,2\")\n")]),
]


def main():
    if len(sys.argv) < 2:
        print("usage: python patch_bridge_60e.py <path-to-bridge.py>")
        return 2
    path = sys.argv[1]
    src = open(path, encoding="utf-8").read()
    applied = already = 0
    out = src
    for i, (marker, variants) in enumerate(EDITS):
        if marker in out:
            already += 1
            continue
        for a, b in variants:
            if out.count(a) == 1:
                out = out.replace(a, b, 1)
                applied += 1
                break
        else:
            print("PATCH FAILED: edit %d found no known state - file NOT patched." % i)
            print("send me your bridge.py and I will re-aim the patch.")
            return 1
    if applied == 0:
        print("already patched (v0.9.60g) - nothing to do")
        return 0
    shutil.copy2(path, path + ".bak-60e")
    open(path, "w", encoding="utf-8", newline="\n").write(out)
    compile(out, path, "exec")
    print("patched OK: %d edit(s) applied, %d already present (backup: %s)"
          % (applied, already, path + ".bak-60e"))
    print("restart the app to reload the bridge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
