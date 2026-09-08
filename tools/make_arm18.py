# make_arm18.py - build ams_board18.ino from ams_board17.ino (anchored, assertive).
# ROOT CAUSE (verified in HID-Project src/HID-APIs/AbsoluteMouseAPI.hpp):
#   press()/release() -> buttons() -> moveTo(xAxis, yAxis, 0): every button report
#   RESENDS the library's stored axes; move(x,y,w) is relative to the same stored axes.
#   The library boots with xAxis=yAxis=0, and on that SIGNED axis 0 = screen CENTRE.
#   The firmware's own pixel tracker (g_curX/g_curY) booted at (0,0) = top-left corner
#   and was never synced into the library -> any click/scroll without a prior
#   board-driven move dragged the cursor to the middle of the monitor (user report:
#   "click step resets the mouse to the centre after clicking", "scroll doesn't work
#   and resets to centre").
# FIXES (fw 1.8):
#   1) tracker boots at the screen centre (Windows' boot cursor position);
#   2) cursor_sync(): every button/wheel report carries the TRACKED position;
#   3) MWHEEL sends the tracked axes with the wheel delta (was move(0,0,d));
#   4) bonus same-family fixes: rel-MMOVE and MDRAG moved by AXIS units (+-127 of
#      32767 ~ 7 px!) instead of pixels - both now go through mouse_move_abs.
import sys

SRC = open("/data/work/arm17/ams_board17.ino", encoding="utf-8").read()
SRC = SRC.replace("\r\n", "\n")   # normalize for anchoring; CRLF restored on write

edits = [
    # 1) version bump + why
    ("#define FW_VER   \"1.7\"",
     "// fw 1.8 (08 Sep 2026): click/wheel no longer drag the cursor to screen centre.\n"
     "//   HID-Project resends its STORED axes on every button/wheel report and those axes\n"
     "//   boot to (0,0) = centre, while our pixel tracker booted at (0,0) = top-left: any\n"
     "//   click/scroll without a prior board-driven move jumped to the middle of the screen.\n"
     "//   Now the tracker boots at centre and every button/wheel report carries the TRACKED\n"
     "//   position (cursor_sync). Bonus: rel-MMOVE and MDRAG moved by AXIS units (+-127 of\n"
     "//   32767 ~ 7 px!) instead of pixels - both go through mouse_move_abs now.\n"
     "#define FW_VER   \"1.8\""),
    # 2) tracker boots at centre (matches Windows' boot cursor; library boots there too)
    ("static int32_t  g_curX = 0, g_curY = 0;   // tracked in screen pixels",
     "static int32_t  g_curX = 960, g_curY = 540;   // fw 1.8 - tracked in screen pixels; boots at centre (Windows' boot cursor), not the corner"),
    # 3) cursor_sync helper right after mouse_move_abs
    ("  g_curX = x; g_curY = y;\n"
     "}\n"
     "\n"
     "static uint8_t parse_button(const char* s) {",
     "  g_curX = x; g_curY = y;\n"
     "}\n"
     "\n"
     "// fw 1.8: make the next button/wheel report carry the TRACKED cursor position.\n"
     "// HID-Project's press/release/wheel resend the library's stored axes, which boot to\n"
     "// (0,0) = screen centre - that was the \"click/scroll jumps to the middle\" bug.\n"
     "static void cursor_sync() {\n"
     "  AbsoluteMouse.moveTo(toAbsX(g_curX), toAbsY(g_curY), 0);\n"
     "}\n"
     "\n"
     "static uint8_t parse_button(const char* s) {"),
    # 4) MCLICK: sync before the press loop
    ("    uint8_t b = parse_button(bs);\n"
     "    if (cnt < 1) cnt = 1;\n"
     "    for (int i = 0; i < cnt; i++) {\n"
     "      AbsoluteMouse.press(b);",
     "    uint8_t b = parse_button(bs);\n"
     "    if (cnt < 1) cnt = 1;\n"
     "    cursor_sync();            // fw 1.8: click at the tracked position, never at centre\n"
     "    for (int i = 0; i < cnt; i++) {\n"
     "      AbsoluteMouse.press(b);"),
    # 5) MDOWN
    ("  if (!strcmp(cmd, \"MDOWN\")) {\n"
     "    AbsoluteMouse.press(parse_button(args));",
     "  if (!strcmp(cmd, \"MDOWN\")) {\n"
     "    cursor_sync();            // fw 1.8\n"
     "    AbsoluteMouse.press(parse_button(args));"),
    # 6) MUP
    ("  if (!strcmp(cmd, \"MUP\"))   {\n"
     "    AbsoluteMouse.release(parse_button(args));",
     "  if (!strcmp(cmd, \"MUP\"))   {\n"
     "    cursor_sync();            // fw 1.8\n"
     "    AbsoluteMouse.release(parse_button(args));"),
    # 7) MDRAG: pixel delta + tracked, not axis units
    ("      uint8_t b = parse_button(bs);\n"
     "      AbsoluteMouse.press(b); delay(60);\n"
     "      AbsoluteMouse.move((int8_t)constrain(dx, -127, 127), (int8_t)constrain(dy, -127, 127), 0); delay(60);\n"
     "      AbsoluteMouse.release(b);",
     "      uint8_t b = parse_button(bs);\n"
     "      cursor_sync();          // fw 1.8\n"
     "      AbsoluteMouse.press(b); delay(60);\n"
     "      mouse_move_abs(g_curX + dx, g_curY + dy, false);   // fw 1.8: drag delta in PIXELS (was axis units)\n"
     "      delay(60);\n"
     "      AbsoluteMouse.release(b);"),
    # 8) MWHEEL: tracked axes + wheel delta (was the centre-jumping move(0,0,d))
    ("  if (!strcmp(cmd, \"MWHEEL\")) {\n"
     "    int d = atoi(args);\n"
     "    AbsoluteMouse.move(0, 0, (int8_t)d);\n"
     "    reply_ok(\"MWHEEL\");",
     "  if (!strcmp(cmd, \"MWHEEL\")) {\n"
     "    int d = atoi(args);\n"
     "    // fw 1.8: the wheel report carries the TRACKED axes. The old move(0,0,d) resent the\n"
     "    // library's boot state (0,0 = screen centre) and dragged the cursor to the middle.\n"
     "    AbsoluteMouse.moveTo(toAbsX(g_curX), toAbsY(g_curY), (int8_t)d);\n"
     "    reply_ok(\"MWHEEL\");"),
    # 9) rel-MMOVE: pixel delta through the tracker (was axis units - barely moved)
    ("      if (!strcmp(mode, \"rel\")) {\n"
     "        AbsoluteMouse.move((int8_t)constrain(x, -127, 127), (int8_t)constrain(y, -127, 127), 0);\n"
     "        g_curX += x;\n"
     "        g_curY += y;\n"
     "      }",
     "      if (!strcmp(mode, \"rel\")) {\n"
     "        // fw 1.8: rel deltas are PIXELS; move() takes AXIS units (+-127 of 32767 ~ 7 px),\n"
     "        // so route through the tracked absolute position.\n"
     "        mouse_move_abs(g_curX + x, g_curY + y, false);\n"
     "      }"),
    # 10) TRGSND armed click: sync before the board-side click
    ("    uint8_t b = (act == 2) ? MOUSE_RIGHT : (act == 3) ? MOUSE_MIDDLE : MOUSE_LEFT;\n"
     "    AbsoluteMouse.press(b); delay((uint16_t)hold); AbsoluteMouse.release(b);",
     "    uint8_t b = (act == 2) ? MOUSE_RIGHT : (act == 3) ? MOUSE_MIDDLE : MOUSE_LEFT;\n"
     "    cursor_sync();            // fw 1.8: the armed click must not jump to centre\n"
     "    AbsoluteMouse.press(b); delay((uint16_t)hold); AbsoluteMouse.release(b);"),
]
for i, (a, b) in enumerate(edits):
    assert SRC.count(a) == 1, "anchor %d not unique (count=%d)" % (i, SRC.count(a))
    SRC = SRC.replace(a, b)

# ---- static proofs ----
assert '#define FW_VER   "1.8"' in SRC and '#define FW_VER   "1.7"' not in SRC
assert "AbsoluteMouse.move(" not in SRC, "a raw AbsoluteMouse.move( call survived"
assert SRC.count("static void cursor_sync()") == 1, "cursor_sync must be defined once"
assert SRC.count("cursor_sync();") == 5, "cursor_sync at MCLICK/MDOWN/MUP/MDRAG/TRGSND (got %d)" % SRC.count("cursor_sync();")
assert SRC.count("{") == SRC.count("}"), "brace imbalance"
base = open("/data/work/arm17/ams_board17.ino", encoding="utf-8").read().replace("\r\n", "\n")
assert SRC.count("{") == base.count("{") + 1, "only cursor_sync adds a brace pair"
# the 1.7 base itself carries 4 unmatched parens in comments/strings; the patch must not
# change the balance either way
assert (SRC.count("(") - SRC.count(")")) == (base.count("(") - base.count(")")), "paren balance changed"
open("/data/work/arm17/ams_board18.ino", "w", encoding="utf-8", newline="\r\n").write(SRC)
print("make_arm18: DONE - ams_board18.ino (%d lines, FW 1.8)" % SRC.count("\n"))
