# make_60e.py - build code60e.py (production) from code60d.py.
# ROOT CAUSES (hardware logs 2026-09-08, ~16:53-17:13):
#  1) SETRES answered by OK|HALT / OK|PONG (reply mis-pairing). The Pico leg of it:
#     forward_to_arm returned the FIRST pending non-mouse arm line - including a stale
#     OK|HALT owed to a write-only abort - as the new command's answer. Fix: drain the
#     arm pipe BEFORE writing a blocking command (two sweeps, 20 ms apart).
#  2) After an aborted dense path, the 60c flow ledger (_arm_lag/_pending_move) survived
#     into the next run: a late arm ack could flush a STALE coalesced move (mystery jump)
#     and the leftover lag made the next run's first path sluggish. Fix: HALT/BYE and
#     SETRES both reset the ledger (_flow_reset).
#  3) Long humanized KTEXT never pumped the arm: an arm with pending acks could fill its
#     tiny TX buffer mid-typing and wedge (the 60c disease, via the keyboard). The USB RX
#     was also unread for the whole chunk. Fix: pump_arm() + drain USB into the main
#     buffer on every typed char.
SRC = open("/data/code60d.py", encoding="utf-8").read()

edits = [
    # 1) _flow_reset helper + forward_to_arm pre-drain
    ("def forward_to_arm(line, timeout_s):\n"
     "    \"\"\"Blocking forward for commands whose reply the PC needs (sound, SETRES, HALT/BYE).\n"
     "    Keeps pumping while waiting so arm EVT| lines still stream to the PC.\"\"\"\n"
     "    head = line.split(\"|\")[0]\n"
     "    if not _arm_write(line):\n"
     "        return \"ERR|NOARM|\" + head\n",
     "def _flow_reset():\n"
     "    \"\"\"v0.9.60e - wipe the 60c mouse flow ledger (HALT/BYE/SETRES): no stale coalesced\n"
     "    move may flush into the next run, and leftover lag must not slow the next path.\"\"\"\n"
     "    global _arm_lag, _pending_move\n"
     "    _arm_lag = 0\n"
     "    _pending_move = None\n"
     "\n\n"
     "def forward_to_arm(line, timeout_s):\n"
     "    \"\"\"Blocking forward for commands whose reply the PC needs (sound, SETRES, HALT/BYE).\n"
     "    Keeps pumping while waiting so arm EVT| lines still stream to the PC.\n"
     "    v0.9.60e - stale-reply guard: whatever the arm still owes when a NEW blocking command\n"
     "    starts belongs to an older (or aborted) command. Drain it BEFORE writing, so a late\n"
     "    OK|HALT can never be mis-paired as the answer to the next SETRES.\"\"\"\n"
     "    head = line.split(\"|\")[0]\n"
     "    pump_arm()                        # v0.9.60e - first sweep of stale arm lines\n"
     "    time.sleep(0.02)                  # v0.9.60e - let an in-flight stale byte land\n"
     "    pump_arm()                        # v0.9.60e - second sweep: the pipe is truly quiet\n"
     "    if not _arm_write(line):\n"
     "        return \"ERR|NOARM|\" + head\n"),
    # 2) HALT/BYE resets the flow ledger
    ("    if line in (\"HALT\", \"BYE\"):\n"
     "        if arm is not None:\n"
     "            forward_to_arm(line, 2)          # stop the arm too\n"
     "        return \"OK|\" + line\n",
     "    if line in (\"HALT\", \"BYE\"):\n"
     "        _flow_reset()                # v0.9.60e - stop wipes the mouse flow ledger\n"
     "        if arm is not None:\n"
     "            forward_to_arm(line, 2)          # stop the arm too\n"
     "        return \"OK|\" + line\n"),
    # 3) SETRES (start of every run/repeat) resets the flow ledger
    ("    if head in ARM_PREFIXES:\n"
     "        tmo = 30 if head in (\"WSND\", \"TRGSND\", \"SCAL\") else 5\n"
     "        return forward_to_arm(line, tmo)\n",
     "    if head in ARM_PREFIXES:\n"
     "        if head == \"SETRES\":\n"
     "            _flow_reset()            # v0.9.60e - a new run starts with a clean ledger\n"
     "        tmo = 30 if head in (\"WSND\", \"TRGSND\", \"SCAL\") else 5\n"
     "        return forward_to_arm(line, tmo)\n"),
    # 4) KTEXT: pump the arm + keep USB RX drained on every typed char
    ("        for ch in txt:\n"
     "            kc, sh = _ascii_key(ch)\n"
     "            if sh:\n"
     "                kbd.press(Keycode.LEFT_SHIFT)\n",
     "        for ch in txt:\n"
     "            pump_arm()               # v0.9.60e - the arm is drained even mid-typing\n"
     "            if serial is not None and serial.in_waiting:   # v0.9.60e - no USB RX overflow\n"
     "                buffer.extend(serial.read(serial.in_waiting))   #   during a long chunk\n"
     "            kc, sh = _ascii_key(ch)\n"
     "            if sh:\n"
     "                kbd.press(Keycode.LEFT_SHIFT)\n"),
    # 5) visible version bump
    ("pico-light 0.9.60d|role=brain",
     "pico-light 0.9.60e|role=brain"),
]
for i, (a, b) in enumerate(edits):
    assert SRC.count(a) == 1, "anchor %d not unique (count=%d)" % (i, SRC.count(a))
    SRC = SRC.replace(a, b)

assert "pico-light 0.9.60e" in SRC
assert "def _flow_reset" in SRC
assert "del buffer[" not in SRC and "del _arm_buf[" not in SRC, "a slice-delete crept back"
assert "kbd.write(" not in SRC, "kbd.write call crept back"
open("/data/code60e.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60e.py", "exec")
print("compile OK")
print("make_60e: DONE")
