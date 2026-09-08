# make_60b.py - build code60b.py (production, clean) from code60a.py.
# ROOT CAUSE (hardware-confirmed by diag3): CircuitPython 10.3.0 bytearray does NOT
# support slice deletion - `del buffer[:nl+1]` raises
#   TypeError("'bytearray' object doesn't support item deletion")
# every time a complete line arrives, and the silent never-die guard swallowed it, so
# PING was never answered (since the 0.9.59h byte-buffer rewrite). Fix = rebind-by-slice
# (`buf = buf[nl+1:]`) instead of slice-delete, in BOTH RX paths (main PC port + the
# arm pump, which has the SAME latent bug and would break the moment the arm answers).
# bytes()/decode() are fine (they did not throw); only the slice-delete did.
SRC = open("/data/code60a.py", encoding="utf-8").read()

edits = [
    # A) pump_arm: declare global + fix the runaway-guard slice-delete
    ("    other reply is returned for a waiting forward_to_arm.\"\"\"\n"
     "    if arm is None:\n"
     "        return []\n"
     "    try:\n"
     "        n = arm.in_waiting\n"
     "        if n:\n"
     "            _arm_buf.extend(arm.read(n))\n"
     "            if len(_arm_buf) > 1024:              # runaway-garbage guard\n"
     "                del _arm_buf[:-256]\n",
     "    other reply is returned for a waiting forward_to_arm.\"\"\"\n"
     "    global _arm_buf   # v0.9.60b - we now rebind-by-slice (CP has no slice-delete)\n"
     "    if arm is None:\n"
     "        return []\n"
     "    try:\n"
     "        n = arm.in_waiting\n"
     "        if n:\n"
     "            _arm_buf.extend(arm.read(n))\n"
     "            if len(_arm_buf) > 1024:              # runaway-garbage guard\n"
     "                _arm_buf = _arm_buf[-256:]         # v0.9.60b - CP-safe (no del-slice)\n"),
    # B) pump_arm: fix the line-consume slice-delete
    ("        raw = bytes(_arm_buf[:nl])\n"
     "        del _arm_buf[:nl + 1]\n",
     "        raw = bytes(_arm_buf[:nl])\n"
     "        _arm_buf = _arm_buf[nl + 1:]             # v0.9.60b - CP-safe (no del-slice)\n"),
    # C) main loop: fix the runaway-guard slice-delete
    ("            if len(buffer) > 4096:            # runaway guard: keep the newest 1 KB\n"
     "                del buffer[:-1024]\n",
     "            if len(buffer) > 4096:            # runaway guard: keep the newest 1 KB\n"
     "                buffer = buffer[-1024:]          # v0.9.60b - CP-safe (no del-slice)\n"),
    # D) main loop: fix the line-consume slice-delete (THE PING killer)
    ("                raw = bytes(buffer[:nl])\n"
     "                del buffer[:nl + 1]\n",
     "                raw = bytes(buffer[:nl])\n"
     "                buffer = buffer[nl + 1:]         # v0.9.60b - CP-safe (no del-slice)\n"),
    # E) visible version bump so the app identity proves the fix is live
    ("pico-light 0.9.60|role=brain",
     "pico-light 0.9.60b|role=brain"),
]
for i, (a, b) in enumerate(edits):
    assert SRC.count(a) == 1, "anchor %d not unique (count=%d)" % (i, SRC.count(a))
    SRC = SRC.replace(a, b)

# static proof: NO slice-deletion may remain on the two bytearray buffers
assert "del buffer[" not in SRC, "main buffer still has a slice-delete"
assert "del _arm_buf[" not in SRC, "arm buffer still has a slice-delete"
assert "pico-light 0.9.60b" in SRC
open("/data/code60b.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60b.py", "exec")
print("compile OK")
print("remaining 'del ' lines:")
for n, l in enumerate(SRC.splitlines(), 1):
    if "del " in l:
        print("  %d: %s" % (n, l.strip()))
print("make_60b: DONE")
