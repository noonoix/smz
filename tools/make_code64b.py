#!/usr/bin/env python3
# make_code64b.py - build code64b.py from code64.py via anchored, count-asserted edits.
import hashlib, os, py_compile, sys

SRC_PATH = "/data/code64/code64.py"
OUT_DIR = "/data/build/pkg"
src = open(SRC_PATH, encoding="utf-8").read()

edits_applied = 0
def rep(old, new):
    global src, edits_applied
    n = src.count(old)
    assert n == 1, "anchor not unique (count=%d): %r" % (n, old[:70])
    src = src.replace(old, new, 1)
    edits_applied += 1

def rep_line(marker, new_line):
    """Replace the single line containing marker (robust to comment spacing)."""
    global src, edits_applied
    lines = src.splitlines(True)
    hits = [i for i, l in enumerate(lines) if marker in l]
    assert len(hits) == 1, "line anchor not unique (count=%d): %r" % (len(hits), marker)
    indent = lines[hits[0]][:len(lines[hits[0]]) - len(lines[hits[0]].lstrip())]
    lines[hits[0]] = indent + new_line + "\n"
    src = "".join(lines)
    edits_applied += 1

# E1 - header version
rep("# Classroom Studio v0.9.64 - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)",
    "# Classroom Studio v0.9.64b - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)")

# E2 - version notes block after the v0.9.64 history entry
rep("#   (ships as code63.py - built from the code62 tree via splice edits)",
    "#   (ships as code63.py - built from the code62 tree via splice edits)\n"
    "#\n"
    "# v0.9.64b - no more start/stop teleport (record analysis 2026-09-09, 14 GP4 toggles):\n"
    "#   arm fw>=1.8 syncs its tracked axes into EVERY button report (cursor_sync), so the\n"
    "#   v0.9.63 unconditional MUP x3 on start/stop teleported the cursor back to the last\n"
    "#   plan point whenever the user had moved the physical mouse while stopped (5 snaps\n"
    "#   of 964-1216 px in the same millisecond as the keypress, each followed by exactly\n"
    "#   three identical position reports = the three MUP reports).\n"
    "#   * release_all_buttons is now CONDITIONAL on the routine GP4 start/stop path: the\n"
    "#     Pico tracks MDOWN/MUP itself (_held_buttons) and releases only genuinely held\n"
    "#     buttons - empty set = zero MUP = zero cursor_sync = zero teleport.\n"
    "#   * force=True keeps the full three-button v0.9.63 shield on the abnormal paths\n"
    "#     (host HALT/BYE, plan abort, plan run error).\n"
    "#   * Panic gesture: holding GP4 >= 1 s force-releases all three buttons + 5 LED flashes.\n"
    "#   * Known limit (unchanged, documented): if the mouse was moved while stopped, the\n"
    "#     plan resumes from its stored position and its first move re-homes the cursor\n"
    "#     into the plan region - HID has no position feedback channel. The complete fix\n"
    "#     for that case is app-side cursor sync on start (queued for the C# line).")

# E3 - PONG version
rep('return "OK|PONG|pico-light 0.9.64|role=brain+keyboard+light|arm=promicro"',
    'return "OK|PONG|pico-light 0.9.64b|role=brain+keyboard+light|arm=promicro"')

# E4 - boot banner
rep('print("pico-light 0.9.64 | GP4=NumLock start/stop | GP3=ScrollLock pause | LED solid=run blink=pause")',
    'print("pico-light 0.9.64b | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause")')

# E5 - _held_buttons global next to the other flow globals
rep("_pending_move = None  # v0.9.60c - newest coalesced absolute MMOVE while the arm is behind",
    "_pending_move = None  # v0.9.60c - newest coalesced absolute MMOVE while the arm is behind\n"
    "_held_buttons = set()  # v0.9.64b - mouse buttons the Pico itself drove down and has not released")

# E6 - track held buttons in forward_fast (unique 3-line tail anchor)
rep('''    if not _arm_write(line):
        return "ERR|NOARM|" + head
    return "OK|" + head''',
    '''    # v0.9.64b - track held buttons so start/stop releases only what is truly held
    if head == "MDOWN" and "|" in line:
        _held_buttons.add(line.split("|")[1].split(",")[0].strip().lower())
    elif head == "MUP" and "|" in line:
        _held_buttons.discard(line.split("|")[1].split(",")[0].strip().lower())
    if not _arm_write(line):
        return "ERR|NOARM|" + head
    return "OK|" + head''')

# E7 - release_all_buttons becomes conditional (force keeps the old behaviour)
rep('''def release_all_buttons():
    """v0.9.63 - panic release: ghost MDOWN/MCLICK corruption on the unframed UART (or
    an arm reset mid-click) can leave a button logically held = Windows unclickable
    until Ctrl+Alt+Del (field evidence 2026-09-09: Right Down at 15.96 s never released).
    Every stop/start/abort releases all three buttons so a held state never survives."""
    for btn in ("left", "right", "middle"):
        _arm_write("MUP|" + btn)''',
    '''def release_all_buttons(force=False):
    """v0.9.63 - panic release: ghost MDOWN/MCLICK corruption on the unframed UART (or
    an arm reset mid-click) can leave a button logically held = Windows unclickable
    until Ctrl+Alt+Del (field evidence 2026-09-09: Right Down at 15.96 s never released).
    v0.9.64b - CONDITIONAL by default: the Pico tracks MDOWN/MUP itself, so a routine
    GP4 start/stop releases only genuinely held buttons. An empty set means ZERO MUP
    traffic - and since arm fw>=1.8 syncs its tracked axes into every button report,
    zero MUP also means zero cursor_sync and zero start/stop teleport (record
    2026-09-09: 5 snaps of 964-1216 px exactly at the keypress). force=True keeps the
    full three-button shield for the abnormal paths (host HALT/BYE, plan abort/run
    error) and for the panic gesture (GP4 held >= 1 s)."""
    targets = ("left", "right", "middle") if force else tuple(sorted(_held_buttons))
    for btn in targets:
        _arm_write("MUP|" + btn)
    _held_buttons.clear()''')

# E8 - call sites: routine start/stop stay conditional; abnormal paths force
rep_line("# v0.9.63 - a start never inherits a held button",
         'release_all_buttons()      # v0.9.64b - tracked-held only (a pointless MUP teleports the cursor)')
rep_line("# v0.9.63 - a stop never leaves a button held",
         'release_all_buttons()     # v0.9.64b - tracked-held only (a pointless MUP teleports the cursor)')
rep_line("# v0.9.63 - an abort never leaves a button held",
         'release_all_buttons(force=True)   # v0.9.64b - full shield on the abort path')
rep_line("# v0.9.63 - a crashed pass never leaves a button held",
         'release_all_buttons(force=True)   # v0.9.64b - full shield on the error path')
rep_line("# v0.9.63 - host stop never leaves a button held",
         'release_all_buttons(force=True)  # v0.9.64b - full shield on host HALT/BYE')

# E9 - panic gesture state + GP4 hold measurement in poll_keypad
rep("engine_paused = False        # GP3 toggles this (Scroll Lock = Pause/Resume)",
    "engine_paused = False        # GP3 toggles this (Scroll Lock = Pause/Resume)\n"
    "_btn1_since = None           # v0.9.64b - GP4 press timestamp for the panic-hold gesture")
rep('''    global engine_on, engine_paused, _last_btn1, _last_btn2''',
    '''    global engine_on, engine_paused, _last_btn1, _last_btn2, _btn1_since''')
rep('''    if b1 and not _last_btn1:
        engine_on = not engine_on''',
    '''    if b1 and not _last_btn1:
        _btn1_since = time.monotonic()   # v0.9.64b - measure the hold for the panic gesture
        engine_on = not engine_on''')
rep('''    _last_btn1 = b1
    _last_btn2 = b2''',
    '''    if not b1 and _last_btn1 and _btn1_since is not None:   # v0.9.64b - GP4 release edge
        if time.monotonic() - _btn1_since >= 1.0:             # >= 1 s hold = panic release
            release_all_buttons(force=True)
            led_fault(5)                                      # 5 flashes = panic release done
        _btn1_since = None
    _last_btn1 = b1
    _last_btn2 = b2''')

os.makedirs(os.path.join(OUT_DIR, "CIRCUITPY-ready"), exist_ok=True)
open(os.path.join(OUT_DIR, "code64b.py"), "w", encoding="utf-8").write(src)
open(os.path.join(OUT_DIR, "CIRCUITPY-ready", "code.py"), "w", encoding="utf-8").write(src)
py_compile.compile(os.path.join(OUT_DIR, "code64b.py"), doraise=True)

# plan_engine.py + plan.txt ship byte-identical
import shutil
shutil.copyfile("/data/code64/plan_engine.py", os.path.join(OUT_DIR, "plan_engine.py"))
shutil.copyfile("/data/code64/CIRCUITPY-ready/plan.txt", os.path.join(OUT_DIR, "plan.txt"))
shutil.copyfile("/data/code64/plan_engine.py", os.path.join(OUT_DIR, "CIRCUITPY-ready", "plan_engine.py"))
shutil.copyfile("/data/code64/CIRCUITPY-ready/plan.txt", os.path.join(OUT_DIR, "CIRCUITPY-ready", "plan.txt"))

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]

print("edits applied:", edits_applied)
print("py_compile: OK")
print("code64b.py  sha256:", sha(os.path.join(OUT_DIR, "code64b.py")), os.path.getsize(os.path.join(OUT_DIR, "code64b.py")), "bytes")
print("plan_engine unchanged:", sha(os.path.join(OUT_DIR, "plan_engine.py")) == sha("/data/code64/plan_engine.py"))
print("plan.txt unchanged:", sha(os.path.join(OUT_DIR, "CIRCUITPY-ready", "plan.txt")) == sha("/data/code64/CIRCUITPY-ready", "plan.txt"))
print("release_all_buttons() bare calls:", src.count("release_all_buttons()"))
print("release_all_buttons(force=True) calls:", src.count("release_all_buttons(force=True)"))
