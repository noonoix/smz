# make_arm19.py - build ams_board19.ino (FW 1.9) from ams_board18.ino with anchored edits.
#
# FW 1.9 = the hand-smoothness firmware. The user's own hand recording (2026-09-09,
# "my hand.txt": 3113 samples / 7.9 s) measures: median 3 px per sample, ~390 samples/sec,
# median speed ~530 px/s. The PC->pico->arm chain physically tops out at ~50 fed
# points/sec (~20 ms each), but the arm alone can emit ~100+ HID reports/sec (its only
# per-report cost is the USB HID frame, ~8-10 ms). So the bridge keeps feeding >=25 ms
# thinned WindMouse points (shape + speed profile preserved in the point spacing), and
# fw 1.9 subdivides each fed segment into <=8 px linear micro-steps at native HID pace
# (MMOVE abs,2) -> ~100 reports/sec, hand-smooth, exact landing.
#
# Backwards compatible: fw 1.8 parses hm==2 as non-human (hm[0] == '1' is strict) and
# simply jumps per fed point - the pre-1.9 behaviour - so a v3.3 bridge + old arm still works.
import sys

BASE = "/data/work/arm17/ams_board18.ino"
OUT = "/data/work/arm17/ams_board19.ino"

src = open(BASE, "r", encoding="utf-8", newline="").read()
eol = "\r\n" if "\r\n" in src else "\n"


def nl(s):   # author with \n, write with the file's own EOL
    return s.replace("\n", eol)


STREAM_FN = nl(
    "\n"
    "// fw 1.9: streamed path point (MMOVE abs,2). The bridge thins paths to >=25 ms points\n"
    "// that already carry the WindMouse speed profile in their spacing; subdivide each fed\n"
    "// segment here into <=8 px linear micro-steps paced by the HID frame (~8-10 ms each)\n"
    "// -> ~100 reports/sec, hand-smooth, and the app-planned curve shape is preserved.\n"
    "// Substeps are capped at 3 so a fast segment never overruns the 25 ms feed cadence.\n"
    "static void mouse_move_stream(int32_t x, int32_t y) {\n"
    "  int32_t dx = x - g_curX, dy = y - g_curY;\n"
    "  uint32_t dist = (uint32_t)sqrt((float)(dx * dx + dy * dy));\n"
    "  uint8_t steps = (uint8_t)(dist / 8);\n"
    "  if (steps > 3) steps = 3;\n"
    "  if (steps < 1) {\n"
    "    AbsoluteMouse.moveTo(toAbsX(x), toAbsY(y));\n"
    "    g_curX = x; g_curY = y;\n"
    "    return;\n"
    "  }\n"
    "  int32_t sx = g_curX, sy = g_curY;\n"
    "  for (uint8_t i = 1; i <= steps; i++) {\n"
    "    int32_t px = sx + (int32_t)((dx * (int32_t)i) / (int32_t)steps);\n"
    "    int32_t py = sy + (int32_t)((dy * (int32_t)i) / (int32_t)steps);\n"
    "    AbsoluteMouse.moveTo(toAbsX(px), toAbsY(py));\n"
    "    delay(1);                       // let the HID frame breathe between sub-reports\n"
    "  }\n"
    "  g_curX = x; g_curY = y;\n"
    "}\n"
)

EDITS = [
    # 1) version bump
    (nl('#define FW_VER   "1.8"'),
     nl('#define FW_VER   "1.9"')),
    # 2) insert mouse_move_stream right after mouse_move_abs (its final line + closing brace)
    (nl("  g_curX = x; g_curY = y;\n}\n"),
     nl("  g_curX = x; g_curY = y;\n}\n") + STREAM_FN),
    # 3) MMOVE abs-mode dispatch: hm==2 -> interpolated stream point (fw 1.8: hm[0]=='1'
    #    is strict, so an old arm reads a 2 as a plain jump - graceful degradation)
    (nl("      else mouse_move_abs(x, y, hm[0] == '1');"),
     nl("      else if (hm[0] == '2') mouse_move_stream(x, y);   // fw 1.9: interpolated path point\n"
        "      else mouse_move_abs(x, y, hm[0] == '1');")),
]

for i, (a, b) in enumerate(EDITS):
    n = src.count(a)
    if n != 1:
        print("ANCHOR FAIL at edit %d (count=%d) - aborting, no file written" % (i, n))
        sys.exit(1)
    src = src.replace(a, b, 1)

# static integrity: brace/paren balance must match the base file exactly
def balance(t):
    return (t.count("{") - t.count("}"), t.count("(") - t.count(")"))

if balance(src) != balance(open(BASE, "r", encoding="utf-8", newline="").read()):
    print("BALANCE FAIL - braces/parens drifted from base")
    sys.exit(1)

for marker in ('#define FW_VER   "1.9"', "mouse_move_stream", "hm[0] == '2'"):
    if marker not in src:
        print("MARKER MISSING: " + marker)
        sys.exit(1)

open(OUT, "w", encoding="utf-8", newline="").write(src)
import hashlib
h = hashlib.sha256(src.encode("utf-8")).hexdigest()
print("built %s (%d lines) sha256 %s" % (OUT, src.count(eol) + 1, h))
