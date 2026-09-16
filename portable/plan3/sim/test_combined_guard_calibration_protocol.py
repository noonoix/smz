#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "portable/plan3/CIRCUITPY"))
from guard_calibration_protocol import build_calibration_get, parse_calibration_set

# Revision tokens reject both field delimiters and line breaks without imposing a hash format.
revision = "guard-0123456789abcdef"
payload, error = parse_calibration_set("CALSET|%s|desktop|10.1|2|750" % revision)
assert error is None
assert payload == {
    "revision": revision,
    "id": "desktop",
    "center": 10.1,
    "tolerance": 2.0,
    "stable_ms": 750,
}
assert build_calibration_get(revision, 6) == "OK|CALGET|revision=%s|count=6" % revision

for line, expected in (
    ("CALSET|bad|revision|desktop|10|2|750", "ARG"),
    ("CALSET|bad\nrevision|desktop|10|2|750", "REVISION"),
    ("CALSET|%s|not-a-profile|10|2|750" % revision, "PROFILE"),
    ("CALSET|%s|desktop|nan|2|750" % revision, "VALUE"),
    ("CALSET|%s|desktop|-1|2|750" % revision, "VALUE"),
    ("CALSET|%s|desktop|10|2|-1" % revision, "VALUE"),
    ("CALSET|%s|desktop|10|2|750|extra" % revision, "ARG"),
):
    parsed, error = parse_calibration_set(line)
    assert parsed is None and error == expected, (line, parsed, error)

portable_helper = (root / "portable/plan3/CIRCUITPY/guard_calibration_protocol.py").read_bytes()
firmware_helper = (root / "firmware/pico-light-guard-1.0.0/guard_calibration_protocol.py").read_bytes()
assert portable_helper == firmware_helper

runtime = (root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py").read_text(encoding="utf-8")
assert "from guard_calibration_protocol import build_calibration_get, parse_calibration_set" in runtime
for phrase in (
    "def calget(self)",
    "def calset(self, line)",
    "_publish_calibration",
    "elif line == \"CALGET\"",
    "elif line.startswith(\"CALSET|\")",
    "ERR|CALSET|BUSY",
    "return \"ERR|CALSET|\" + error",
):
    assert phrase in runtime, phrase

print("combined Guard calibration protocol: CALGET, CALSET validation, persistence parity and runtime integration verified")
