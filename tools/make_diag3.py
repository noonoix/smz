# make_diag3.py - build code60a-diag3.py from the PROVEN code60a.py.
# Hardware evidence: the PING chunk ARRIVES and is logged (hex 50494e470a) but the line
# is NEVER assembled (no DIAG rx line). pump_arm proves bytearray.find works (it runs
# every loop without killing the loop), so the failure is in the PARSE step:
# bytes(bytearray) / del-slice / bytes.decode - introduced by the 0.9.59h byte-buffer
# rewrite, silently swallowed by the never-die guard. (The old string-buffer build
# answered PING fine.) diag3 = manual CP-safe newline scan + primary parse wrapped
# (logs the exact failing op) + chr-based fallback that answers PING regardless.
SRC = open("/data/code60a.py", encoding="utf-8").read()

# --- injection 1: helpers + import sys + banner (+ CircuitPython version) ---
a1 = ("engine_on = AUTOSTART        # GP4 toggles this (Num Lock = Start/Stop)\n"
      "engine_paused = False        # GP3 toggles this (Scroll Lock = Pause/Resume)\n"
      "last_host_cmd = time.monotonic()\n")
n1 = (a1 + "\n"
      "import sys as _sys\n"
      "\n\n"
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
      "_diag_print(\"DIAG60a-diag3 boot | hid=\" + (\"yes\" if kbd is not None else \"no\")\n"
      "            + \" | dataport=\" + (\"yes\" if usb_cdc.data is not None else \"no\")\n"
      "            + \" | sensor=\" + (\"yes\" if sensor is not None else \"no\")\n"
      "            + \" | arm=\" + (\"yes\" if arm is not None else \"no\"))\n"
      "try:\n"
      "    _diag_print(\"DIAG sys: \" + _sys.version)\n"
      "except Exception:\n"
      "    pass\n")
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

# --- injection 3: CP-safe manual scan + primary parse (logs failing op) + chr fallback ---
a3 = ("            while True:\n"
      "                nl = buffer.find(b\"\\n\")\n"
      "                if nl < 0:\n"
      "                    break\n"
      "                raw = bytes(buffer[:nl])\n"
      "                del buffer[:nl + 1]\n"
      "                line = raw.decode(\"utf-8\").strip()   # v0.9.60a - plain decode (see pump_arm)\n"
      "                if not line:\n"
      "                    continue\n"
      "                last_host_cmd = time.monotonic()\n"
      "                try:\n"
      "                    _serial_write_line(handle(line))\n"
      "                except Exception:\n"
      "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n")
n3 = ("            while True:\n"
      "                nl = -1\n"
      "                for _i in range(len(buffer)):\n"
      "                    if buffer[_i] == 10:\n"
      "                        nl = _i\n"
      "                        break\n"
      "                _diag_print(\"DIAG scan nl=\" + str(nl) + \" buflen=\" + str(len(buffer)))\n"
      "                if nl < 0:\n"
      "                    break\n"
      "                line = None\n"
      "                try:\n"
      "                    _raw = bytes(buffer[:nl])\n"
      "                    line = _raw.decode(\"utf-8\").strip()\n"
      "                    buffer = buffer[nl + 1:]\n"
      "                    _diag_print(\"DIAG primary-parse OK\")\n"
      "                except Exception as _e:\n"
      "                    _diag_print(\"DIAG primary-parse EXC \" + repr(_e))\n"
      "                    try:\n"
      "                        line = \"\"\n"
      "                        for _i in range(nl):\n"
      "                            _b = buffer[_i]\n"
      "                            if _b != 13:\n"
      "                                line += chr(_b)\n"
      "                        line = line.strip()\n"
      "                        buffer = buffer[nl + 1:]\n"
      "                        _diag_print(\"DIAG fallback-parse OK\")\n"
      "                    except Exception as _e2:\n"
      "                        _diag_print(\"DIAG fallback-parse EXC \" + repr(_e2))\n"
      "                        break\n"
      "                _diag_print(\"DIAG rx line: [\" + str(line) + \"]\")\n"
      "                if not line:\n"
      "                    continue\n"
      "                last_host_cmd = time.monotonic()\n"
      "                try:\n"
      "                    _reply = handle(line)\n"
      "                    _diag_print(\"DIAG tx: \" + str(_reply))\n"
      "                    _serial_write_line(_reply)\n"
      "                except Exception as _e:\n"
      "                    _diag_print(\"DIAG tx EXC \" + repr(_e))\n"
      "                    _serial_write_line(\"ERR|EXC|\" + line.split(\"|\")[0])\n")
assert SRC.count(a3) == 1, "anchor 3 not unique"
SRC = SRC.replace(a3, n3)

# --- injection 4: heartbeat in the idle branch ---
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

# --- injection 5: the never-die guard SPEAKS (was silent) ---
a5 = ("    except Exception:\n"
      "        # v0.9.60 - never-die: a bad line or a transient USB hiccup must never kill\n"
      "        # code.py. (KeyboardInterrupt/Ctrl+C still stops it - it is not an Exception.)\n"
      "        try:\n"
      "            time.sleep(0.05)\n"
      "        except Exception:\n"
      "            pass\n")
n5 = ("    except Exception as _e:\n"
      "        # v0.9.60-diag3 - never-die, but SPEAK: log the real error to the console.\n"
      "        _diag_print(\"DIAG loop EXC \" + repr(_e))\n"
      "        try:\n"
      "            time.sleep(0.05)\n"
      "        except Exception:\n"
      "            pass\n")
assert SRC.count(a5) == 1, "anchor 5 not unique"
SRC = SRC.replace(a5, n5)

open("/data/code60a-diag3.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60a-diag3.py", "exec")
print("compile OK")
for m in ("DIAG60a-diag3 boot", "DIAG sys:", "DIAG rx chunk", "DIAG scan nl=",
          "DIAG primary-parse OK", "DIAG primary-parse EXC", "DIAG fallback-parse OK",
          "DIAG rx line: [", "DIAG tx: ", "DIAG tx EXC", "DIAG alive", "DIAG loop EXC"):
    assert m in SRC, "missing marker: " + m
print("all markers present")
print("keypad intact:", "Keycode.KEYPAD_NUMLOCK" in SRC and "poll_keypad" in SRC)
print("make_diag3: DONE")
