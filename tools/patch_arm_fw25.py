#!/usr/bin/env python3
# Classroom Studio - patch_arm_fw25.py
#
# ams_board24.ino (fw 2.4) -> ams_board25.ino (fw 2.5)
#
# Field evidence, run 08:58:44 + recorder 09:01 (Pico 0.9.64e):
#   * zero CKSUM drops, zero NOFRAME drops, lag never above 1
#   * yet the recorder still caught ONE excursion: the cursor glided far left to
#     (305,458) and then snapped back to (1651,82), d=1398
#   * the Pico's own sent-stream watchdog printed nothing at that moment
#
# A target the Pico never sent, that the frame checker never rejected, was still
# executed. The remaining path is a line that is corrupt but whose byte-sum still
# matches (a dropped chunk summing to 0 mod 256, or a short UART write splicing two
# frames). fw 2.5 makes that observable and harmless:
#
#   1. the RAW wire bytes of every line are kept before unwrapping (g_rawLine1)
#   2. a streamed path point further than MOVE_SANITY_PX from the tracked position
#      is REFUSED, and the arm emits EVT|BADMOVE|n|x,y|from=..|raw=<exact bytes>
#      which the Pico forwards straight into the PC capture
#
# MOVE_SANITY_PX is 700: the Pico coalesces mid-path points, so gaps of a few
# hundred px are legitimate (the 09:01 log shows up to 437), while the corrupted
# targets are 1100-1400 px out. A refused point costs one path sample, nothing more.
#
# Usage: python3 patch_arm_fw25.py ams_board24.ino [-o ams_board25.ino]

import argparse, hashlib, sys

GUARD = '''      else if (hm[0] == '2') {
        // fw 2.5: forensics + last line of defence. A streamed path point sits a few
        // dozen px from the tracked position (the brain coalesces, so a few hundred px
        // is still legitimate), but a jump beyond MOVE_SANITY_PX can only be a corrupt
        // line that matched its checksum anyway - the '1216' -> '216' digit drop.
        // Refuse it and echo the RAW wire bytes so the brain log shows what arrived.
        int32_t ddx = (int32_t)x - g_curX, ddy = (int32_t)y - g_curY;
        if (ddx * ddx + ddy * ddy > (int32_t)MOVE_SANITY_PX * (int32_t)MOVE_SANITY_PX) {
          g_badMoves++;
          Serial1.print(F("EVT|BADMOVE|")); Serial1.print(g_badMoves);
          Serial1.print('|'); Serial1.print(x); Serial1.print(','); Serial1.print(y);
          Serial1.print(F("|from=")); Serial1.print(g_curX); Serial1.print(',');
          Serial1.print(g_curY); Serial1.print(F("|raw=")); Serial1.println(g_rawLine1);
          Serial1.flush();
          reply_ok("MMOVE");                             // keep the brain's ack ledger sane
          return;
        }
        mouse_move_stream(x, y);                         // fw 1.9: interpolated path point
      }'''

EDITS = [
    (
        "version",
        '#define FW_VER   "2.4"',
        '#define FW_VER   "2.5"',
    ),
    (
        "sanity state",
        "static bool g_framedLink = false;  // fw 2.4: a valid '#' frame was seen on Serial1",
        "static bool g_framedLink = false;  // fw 2.4: a valid '#' frame was seen on Serial1\n"
        "#define MOVE_SANITY_PX 700         // fw 2.5: no legitimate path point hops this far\n"
        "static uint16_t g_badMoves = 0;    // fw 2.5: streamed targets refused as impossible\n"
        "static char g_rawLine1[MAX_PT];    // fw 2.5: the wire bytes, kept before unwrapping",
    ),
    (
        "raw line capture",
        "      g_line1[g_line1Len] = 0;\n"
        "      g_line1Len = 0;\n"
        "      if (!frame_unwrap(g_line1)) {",
        "      g_line1[g_line1Len] = 0;\n"
        "      g_line1Len = 0;\n"
        "      strncpy(g_rawLine1, g_line1, MAX_PT - 1);  // fw 2.5: forensics copy\n"
        "      g_rawLine1[MAX_PT - 1] = 0;\n"
        "      if (!frame_unwrap(g_line1)) {",
    ),
    (
        "stream sanity guard",
        "      else if (hm[0] == '2') mouse_move_stream(x, y);   // fw 1.9: interpolated path point",
        GUARD,
    ),
    (
        "ver reply counter",
        'snprintf(b, sizeof(b), "OK|VER|%s|absMouse=1|sound=1|enc=1%s", FW_VER,',
        'snprintf(b, sizeof(b), "OK|VER|%s|absMouse=1|sound=1|enc=1|badmoves=%u%s", FW_VER, (unsigned)g_badMoves,',
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = open(a.path, encoding="utf-8", errors="surrogateescape").read()
    out = src
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            print("FAIL: anchor %r found %d times (expected 1)" % (name, n))
            return 1
        out = out.replace(old, new, 1)

    checks = [
        ('#define FW_VER   "2.5"' not in out, "FW_VER was not bumped"),
        ("EVT|BADMOVE|" not in out, "the forensic event is missing"),
        (out.index("#define MOVE_SANITY_PX") > out.index("MOVE_SANITY_PX * (int32_t)"),
         "MOVE_SANITY_PX used before it is defined"),
        (out.index("static char g_rawLine1") > out.index("strncpy(g_rawLine1"),
         "g_rawLine1 used before it is declared"),
        (out.index("strncpy(g_rawLine1") > out.index("if (!frame_unwrap(g_line1))"),
         "raw copy taken after the line was unwrapped in place"),
        ("if (g_framedLink) return false;" not in out, "fw 2.4 strict framing was lost"),
        ("#define BRAIN_BAUD 57600UL" not in out, "fw 2.4 baud was lost"),
        (out.count("mouse_move_stream(x, y)") != 1, "the stream call is no longer unique"),
        (out.count("g_badMoves++") != 1, "the refusal counter is not incremented once"),
    ]
    for bad, msg in checks:
        if bad:
            print("FAIL: " + msg)
            return 1

    if out.count("{") != out.count("}"):
        print("FAIL: unbalanced braces (%d open, %d close)" % (out.count("{"), out.count("}")))
        return 1

    dest = a.out or a.path
    open(dest, "w", encoding="utf-8", errors="surrogateescape").write(out)
    print("PASS: %d edits applied -> %s" % (len(EDITS), dest))
    print("bytes  : %d" % len(out.encode("utf-8", errors="surrogateescape")))
    print("sha256 : %s" % hashlib.sha256(out.encode("utf-8", errors="surrogateescape")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
