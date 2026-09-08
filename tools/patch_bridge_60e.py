# patch_bridge_60e.py - patch the release's bridge.py in place (idempotent).
#
# ROOT CAUSE (hardware log 2026-09-08, runs of 16:53-16:55): on the Pico path, the bridge's
# PicoLink.command() returned the FIRST non-EVT line waiting on the wire - including stale
# answers owed to write-only abort HALTs and late PONGs from send_path's drain pings. That
# mis-paired replies all run long (the user's log: SETRES <- OK|HALT, then SETRES <- OK|PONG
# on every repeat) and left the pipe dirty for the next run (the 17:13 playScript hang).
#
# Fixes (ASCII anchors only - safe against code-page mangling of the Persian comments):
#  1) PicoLink.command: skip stale replies - OK|X / ERR|?|X whose X is not this command's
#     head are eaten (PING's answer is PONG). Real ERRs of THIS command pass through.
#  2) worker: before every send / send_path, drain whatever the pipe still owes
#     (PicoLink only; the encrypted BoardLink already resyncs). Zero cost on a quiet pipe.
#  3) KTEXT gets a payload-sized timeout (len x hmax + margin) - humanized typing of a long
#     text legitimately takes minutes; the flat 5 s default killed it.
#
# Usage:  python patch_bridge_60e.py "C:\...\ClassroomStudio\bridge\bridge.py"
import shutil
import sys


def main():
    if len(sys.argv) < 2:
        print("usage: python patch_bridge_60e.py <path-to-bridge.py>")
        return 2
    path = sys.argv[1]
    src = open(path, encoding="utf-8").read()
    if "_drain_stale" in src and "_ktext_timeout" in src:
        print("already patched (v0.9.60e) - nothing to do")
        return 0

    edits = [
        # 1a) compute the expected reply head before the read loop
        ("        self._send(cmd)\n"
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
         "        while True:\n"),
        # 1b) the stale skip right before the reply is returned
        ("                continue\n"
         "            return line\n",
         "                continue\n"
         "            parts = line.split(\"|\")\n"
         "            if len(parts) >= 2 and parts[0] == \"OK\" and parts[1] and parts[1] != want:\n"
         "                continue                 # v0.9.60e - stale OK of an older command\n"
         "            if len(parts) >= 3 and parts[0] == \"ERR\" and parts[2] and parts[2] != expect:\n"
         "                continue                 # v0.9.60e - stale ERR of an older command\n"
         "            return line\n"),
        # 2) the two helpers, right before open_link
        ("def open_link(port):\n",
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
         "def open_link(port):\n"),
        # 3) drain + sized timeout on the send op
        ("                    cmd = req[\"cmd\"]\n"
         "                    abort_flag.clear()\n"
         "                    reply = link.command(cmd, timeout=req.get(\"timeout\", 5.0))\n",
         "                    cmd = req[\"cmd\"]\n"
         "                    abort_flag.clear()\n"
         "                    _drain_stale(link)         # v0.9.60e - eat leftovers of write-only aborts\n"
         "                    reply = link.command(cmd, timeout=_ktext_timeout(cmd, req.get(\"timeout\", 5.0)))\n"),
        # 4) drain before streaming a dense path
        ("                    aborted = False\n"
         "                    t0 = time.monotonic()\n",
         "                    _drain_stale(link)         # v0.9.60e - clean pipe before streaming\n"
         "                    aborted = False\n"
         "                    t0 = time.monotonic()\n"),
    ]
    for i, (a, b) in enumerate(edits):
        n = src.count(a)
        if n != 1:
            print("PATCH FAILED: anchor %d not unique (count=%d) - file not patched." % (i, n))
            print("send me your bridge.py and I will re-aim the patch.")
            return 1
        src = src.replace(a, b)

    shutil.copy2(path, path + ".bak-60e")
    open(path, "w", encoding="utf-8", newline="\n").write(src)
    compile(src, path, "exec")
    print("patched OK (backup: %s) - restart the app to reload the bridge" % (path + ".bak-60e",))
    return 0


if __name__ == "__main__":
    sys.exit(main())
