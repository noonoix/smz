#!/usr/bin/env python3
# Classroom Studio - patch_arm_fw24.py
# ams_board23.ino (fw 2.3) -> ams_board24.ino (fw 2.4): strict framing + 57600 brain link.
#
# Why: fw 2.3's frame_unwrap() starts with
#   if (line[0] != '#') return true;   // legacy: pass through
# A Serial1 RX-buffer overflow eats a multi-byte chunk that can swallow the
# '#XX|' header of the next line, so the header-less remnant ("MMOVE|349,520")
# was executed unchecked -> the measured ~1000 px teleport.
#
# fw 2.4: once a valid frame has been seen on the link, header-less lines are
# refused (ERR|NOFRAME). Before the first frame the legacy path still works, so
# an old Pico (0.9.64b, or ARM_FRAMING=False) keeps running.
import argparse, hashlib, sys

EDITS = [
    (
        "version",
        '#define FW_VER   "2.3"',
        '#define FW_VER   "2.4"',
    ),
    (
        "brain link baud",
        "  Serial1.begin(115200);   // fw 1.7: brain link (pins 0=RX, 1=TX)",
        "  Serial1.begin(BRAIN_BAUD);   // fw 2.4: 57600 - double the edge margin on the BSS138 shifter",
    ),
    (
        "baud + strict-framing state",
        "static bool frame_unwrap(char* line) {\n"
        "  if (line[0] != '#') return true;               // legacy: pass through",
        "#define BRAIN_BAUD 57600UL   // fw 2.4: must match ARM_BAUD in the Pico's code.py\n"
        "static bool g_framedLink = false;  // fw 2.4: a valid '#' frame was seen on Serial1\n"
        "\n"
        "static bool frame_unwrap(char* line) {\n"
        "  if (line[0] != '#') {\n"
        "    // fw 2.4: STRICT. An RX overflow can eat a whole '#XX|' header, and fw 2.3\n"
        "    // executed the header-less remnant (a truncated MMOVE dragged the cursor\n"
        "    // ~1000 px). Once the link has proven it frames, bare lines are never run.\n"
        "    if (g_framedLink) return false;\n"
        "    return true;                                 // legacy Pico (fw <= 2.3 protocol)\n"
        "  }",
    ),
    (
        "mark framed link",
        "  if (sum != want) return false;                 // corrupted on the wire: never execute\n"
        "  memmove(line, payload, strlen(payload) + 1);   // unwrap in place\n"
        "  return true;",
        "  if (sum != want) return false;                 // corrupted on the wire: never execute\n"
        "  g_framedLink = true;                           // fw 2.4: latch strict mode\n"
        "  memmove(line, payload, strlen(payload) + 1);   // unwrap in place\n"
        "  return true;",
    ),
    (
        "error code",
        '        g_out = &Serial1; reply_err("CKSUM"); g_out = 0;',
        '        g_out = &Serial1; reply_err(g_line1[0] == \'#\' ? "CKSUM" : "NOFRAME"); g_out = 0;',
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    out = open(a.path, encoding="utf-8", errors="replace").read()
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            print("FAIL: anchor %r found %d times (expected 1)" % (name, n))
            return 1
        out = out.replace(old, new, 1)

    checks = [
        ('#define FW_VER   "2.4"' not in out, "version not bumped"),
        ("if (g_framedLink) return false;" not in out, "strict framing missing"),
        ("g_framedLink = true;" not in out, "strict mode never latches"),
        ("Serial1.begin(BRAIN_BAUD)" not in out, "brain link still hard-coded"),
        ("#define BRAIN_BAUD 57600UL" not in out, "baud define missing"),
        ('reply_err("NOFRAME")' in out, "NOFRAME must be chosen dynamically, not always"),
        (out.index("#define BRAIN_BAUD") > out.index("void setup()"),
         "BRAIN_BAUD defined after setup() - would not compile"),
        (out.index("static bool g_framedLink") > out.index("static bool frame_unwrap"),
         "g_framedLink declared after use"),
    ]
    for bad, msg in checks:
        if bad:
            print("FAIL: " + msg)
            return 1

    open(a.out, "w", encoding="utf-8").write(out)
    print("PASS: %d edits applied -> %s" % (len(EDITS), a.out))
    print("bytes  : %d" % len(out.encode("utf-8")))
    print("sha256 : %s" % hashlib.sha256(out.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
