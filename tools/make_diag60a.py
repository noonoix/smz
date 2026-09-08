# make_diag60a.py - build code60a-diag.py from the PROVEN code60a.py by injecting
# DIAG console logging (data before guesses). The keypad path is untouched.
# Every anchor must match exactly once (splice discipline).
import difflib

SRC = open("/data/code60a.py", encoding="utf-8").read()

# --- injection 1: diag helpers + boot banner (after last_host_cmd init) ---
a1 = ("engine_on = AUTOSTART        # GP4 toggles this (Num Lock = Start/Stop)\n"
      "engine_paused = False        # GP3 toggles this (Scroll Lock = Pause/Resume)\n"
      "last_host_cmd = time.monotonic()\n")
n1 = (a1 + "\n"
      "def _diag_hex(b, limit=16):\n"
      "    _h = \"0123456789abcdef\"\n"
      "    _o = []\n"
      "    for _x in b[:limit]:\n"
      "        _o.append(_h[_x >> 4] + _h[_x & 15])\n"
      "    return \"\".join(_o)\n"
      "\n\n"
      "def _diag_print(msg):\n"
      "    # never block the loop when nobody reads the console (pico_console detached)\n"
      "    try:\n"
      "        _c = usb_cdc.console\n"
      "        if _c is not None and getattr(_c, \"connected\", True):\n"
      "            print(msg)\n"
      "    except Exception:\n"
      "        pass\n"
      "\n\n"
      "_diag_beat = time.monotonic()\n"
      "_diag_print(\"DIAG60a boot ok | fw=0.9.60a-diag | hid=\" + (\"yes\" if kbd is not None else \"no\")\n"
      "            + \" | dataport=\" + (\"yes\" if usb_cdc.data is not None else \"no\")\n"
      "            + \" | sensor=\" + (\"yes\" if sensor is not None else \"no\")\n"
      "            + \" | arm=\" + (\"yes\" if arm is not None else \"no\"))\n")
assert SRC.count(a1) == 1, "anchor 1 not unique"
SRC = SRC.replace(a1, n1)

# --- injection 2: log every chunk that arrives on the data port ---
a2 = ("        if serial is not None and serial.in_waiting:\n"
      "            buffer.extend(serial.read(serial.in_waiting))\n")
n2 = ("        if serial is not None and serial.in_waiting:\n"
      "            _chunk = serial.read(serial.in_waiting)\n"
      "            _diag_print(\"DIAG rx chunk n=\" + str(len(_chunk)) + \" hex=\" + _diag_hex(_chunk))\n"
      "            buffer.extend(_chunk)\n")
assert SRC.count(a2) == 1, "anchor 2 not unique"
SRC = SRC.replace(a2, n2)

# --- injection 3: log every assembled line and every reply ---
a3 = ("                line = raw.decode(\"utf-8\").strip()   # v0.9.60a - plain decode (see pump_arm)\n"
      "                if not line:\n"
      "                    continue\n"
      "                last_host_cmd = time.monotonic()\n"
      "                try:\n"
      "                    _serial_write_line(handle(line))\n"
      "                except Exception:\n"
      "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n")
n3 = ("                line = raw.decode(\"utf-8\").strip()   # v0.9.60a - plain decode (see pump_arm)\n"
      "                if not line:\n"
      "                    continue\n"
      "                _diag_print(\"DIAG rx line: \" + line)\n"
      "                last_host_cmd = time.monotonic()\n"
      "                try:\n"
      "                    _reply = handle(line)\n"
      "                    _diag_print(\"DIAG tx: \" + str(_reply))\n"
      "                    _serial_write_line(_reply)\n"
      "                except Exception:\n"
      "                    _diag_print(\"DIAG tx ERR|EXC|\" + line.split(\"|\")[0])\n"
      "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n")
assert SRC.count(a3) == 1, "anchor 3 not unique"
SRC = SRC.replace(a3, n3)

# --- injection 4: heartbeat in the idle branch (keypad branch is untouched) ---
a4 = ("            if engine_on and not engine_paused and host_quiet and states and loop_due():\n"
      "                standalone_pass()\n"
      "                passes += 1\n"
      "            time.sleep(0.02)\n")
n4 = ("            if engine_on and not engine_paused and host_quiet and states and loop_due():\n"
      "                standalone_pass()\n"
      "                passes += 1\n"
      "            if time.monotonic() - _diag_beat >= 2.0:\n"
      "                _diag_beat = time.monotonic()\n"
      "                _diag_print(\"DIAG alive | hid=\" + (\"yes\" if kbd is not None else \"no\"))\n"
      "            time.sleep(0.02)\n")
assert SRC.count(a4) == 1, "anchor 4 not unique"
SRC = SRC.replace(a4, n4)

# --- integrity: the ONLY removed original lines are the two we rewrote ---
orig = open("/data/code60a.py", encoding="utf-8").read().splitlines()
removed = [l[1:] for l in difflib.unified_diff(orig, SRC.splitlines(), lineterm="") if l.startswith("-") and not l.startswith("---")]
expected_removed = {"            buffer.extend(serial.read(serial.in_waiting))",
                    "                    _serial_write_line(handle(line))"}
assert set(removed) == expected_removed, "unexpected removed lines: %r" % (removed,)
print("integrity OK: only the two intended lines were rewritten; everything else is byte-identical")

open("/data/code60a-diag.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60a-diag.py", "exec")
print("compile OK")
print("DIAG lines injected:", SRC.count("_diag_print("))
print("make_diag60a: DONE")
