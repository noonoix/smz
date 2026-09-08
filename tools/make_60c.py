# make_60c.py - build code60c.py (production) from code60b.py.
# WEDGE ROOT CAUSE (hardware log): the firmware fire-and-acks EVERY MMOVE micro-step
# (OK|MMOVE) to the PC. In a dense send_path (241 moves) that is 241 USB writes, but the
# PC only drains 1 line per 12 moves (periodic PING). The Pico's USB TX buffer backs up,
# _serial_write_line blocks, the loop stops reading USB RX, the PC's write buffer fills
# -> "Write timeout" -> the link wedges (and stale OK|MMOVE acks get mis-paired as
# replies to SETRES/KCOMBO). Mouse movement is always sent via send_path which is
# WRITE-ONLY (never reads per-move acks) + a periodic PING, so the per-move ack is pure
# backlog. Fix = MMOVE fire-and-forget + arm flow control with absolute-move coalescing.
SRC = open("/data/code60b.py", encoding="utf-8").read()

edits = [
    ("_arm_buf = bytearray()\n",
     "_arm_buf = bytearray()\n"
     "_arm_lag = 0          # v0.9.60c - MMOVEs written to the arm minus the arm's OK|MMOVE acks\n"
     "_pending_move = None  # v0.9.60c - newest coalesced absolute MMOVE while the arm is behind\n"
     "ARM_LAG_MAX = 8       # v0.9.60c - coalesce dense mouse moves once the arm is this far behind\n"),
    ("def forward_fast(line):\n"
     "    \"\"\"v0.9.60 - mouse fast path: forward to the arm and answer the PC at once; the\n"
     "    pump later collects and discards the arm's own OK.\"\"\"\n"
     "    head = line.split(\"|\")[0]\n"
     "    if not _arm_write(line):\n"
     "        return \"ERR|NOARM|\" + head\n"
     "    return \"OK|\" + head\n",
     "def forward_fast(line):\n"
     "    \"\"\"v0.9.60c - mouse fast path. Discrete clicks/wheel still fire-and-ack. Dense\n"
     "    MMOVE (streamed by send_path, which never reads per-move acks) is fire-and-forget\n"
     "    AND flow-controlled: when the arm falls ARM_LAG_MAX behind we coalesce to the\n"
     "    newest absolute target instead of blocking the USB read (the old per-move OK|MMOVE\n"
     "    ack backed up USB TX - the PC reads only 1 per 12 - and wedged the link).\"\"\"\n"
     "    global _arm_lag, _pending_move\n"
     "    head = line.split(\"|\")[0]\n"
     "    if head == \"MMOVE\":\n"
     "        if _arm_lag >= ARM_LAG_MAX:\n"
     "            _pending_move = line          # absolute move: the newest target wins\n"
     "            return None                   # no per-move ack (send_path never reads them)\n"
     "        if _arm_write(line):\n"
     "            _arm_lag += 1\n"
     "        else:\n"
     "            return \"ERR|NOARM|MMOVE\"\n"
     "        return None                       # no per-move ack\n"
     "    if not _arm_write(line):\n"
     "        return \"ERR|NOARM|\" + head\n"
     "    return \"OK|\" + head\n"),
    ("    global _arm_buf   # v0.9.60b - we now rebind-by-slice (CP has no slice-delete)\n",
     "    global _arm_buf, _arm_lag, _pending_move   # v0.9.60c - rebind-by-slice + mouse flow control\n"),
    ("        if len(parts) > 1 and parts[0] == \"OK\" and parts[1] in MOUSE_PREFIXES:\n"
     "            continue                              # the PC already got its fire-and-ack\n",
     "        if len(parts) > 1 and parts[0] == \"OK\" and parts[1] in MOUSE_PREFIXES:\n"
     "            if parts[1] == \"MMOVE\":               # v0.9.60c - the arm caught up one move\n"
     "                if _arm_lag > 0:\n"
     "                    _arm_lag -= 1\n"
     "                if _pending_move is not None and _arm_lag < ARM_LAG_MAX:\n"
     "                    if _arm_write(_pending_move):   # flush the coalesced latest target\n"
     "                        _arm_lag += 1\n"
     "                    _pending_move = None\n"
     "            continue                              # mouse OKs are never forwarded to the PC\n"),
    ("                try:\n"
     "                    _serial_write_line(handle(line))\n"
     "                except Exception:\n"
     "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n",
     "                try:\n"
     "                    _reply = handle(line)\n"
     "                    if _reply is not None:        # v0.9.60c - MMOVE is fire-and-forget (None)\n"
     "                        _serial_write_line(_reply)\n"
     "                except Exception:\n"
     "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n"),
    ("pico-light 0.9.60b|role=brain",
     "pico-light 0.9.60c|role=brain"),
]
for i, (a, b) in enumerate(edits):
    assert SRC.count(a) == 1, "anchor %d not unique (count=%d)" % (i, SRC.count(a))
    SRC = SRC.replace(a, b)

assert "del buffer[" not in SRC and "del _arm_buf[" not in SRC, "a slice-delete crept back"
assert "pico-light 0.9.60c" in SRC
open("/data/code60c.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60c.py", "exec")
print("compile OK")
print("make_60c: DONE")
