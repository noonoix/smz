#!/usr/bin/env python3
"""Bump the Classroom Studio release pins: app 0.9.60 -> 0.9.64, Pico bundle -> 0.9.64b.

Why: PR #13 shipped PicoFirmwareExporter.BundleVersion = 0.9.64b but left the
csproj version, the startup banner and every pin guard in tests/TestRunner.cs at
0.9.60, so CI run #19 failed 12 version-pin assertions on main (issue #14).

The app keeps a plain numeric version (0.9.64) because MSBuild rejects 0.9.64b.
The firmware bundle keeps its letter revision (0.9.64b) so the exported code.py
stays byte-identical to the golden firmware/code64b/code64b.py. The meta guard in
TestRunner only reads the 0.9.<digits> part, so 0.9.64b counts as 64 and the whole
version family stays consistent.

Idempotent: a second run finds nothing to do and still exits 0.
"""
import pathlib
import re
import sys

APP = "0.9.64"
BUNDLE = "0.9.64b"
BS = chr(92)            # a single backslash
ESCQ = BS + '"'         # the two characters  \" as they appear inside C# string literals

CSPROJ = "ams-shell/src/Ams.UI/Ams.UI.csproj"
VM = "ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs"
EXPORTER = "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
RUNNER = "tests/TestRunner.cs"

# (file, old, new, minimum expected occurrences)
EDITS = [
    (CSPROJ, "<Version>0.9.60</Version>", "<Version>" + APP + "</Version>", 1),
    (VM, "Classroom Studio v0.9.60", "Classroom Studio v" + APP, 1),
    (RUNNER, "<Version>0.9.60</Version>", "<Version>" + APP + "</Version>", 20),
    (RUNNER, "Classroom Studio v0.9.60", "Classroom Studio v" + APP, 15),
    (RUNNER, "BundleVersion = " + ESCQ + "0.9.60" + ESCQ,
             "BundleVersion = " + ESCQ + BUNDLE + ESCQ, 8),
    (RUNNER, 'BundleVersion == "0.9.60"', 'BundleVersion == "' + BUNDLE + '"', 2),
    (RUNNER, "BundleVersion is 0.9.60", "BundleVersion is " + BUNDLE, 1),
    (RUNNER, "csproj version is 0.9.60", "csproj version is " + APP, 2),
    (RUNNER, "pico-light 0.9.60", "pico-light " + BUNDLE, 1),
    (RUNNER, "var curMinor = 60;", "var curMinor = 64;", 1),
]


def meta_pins(text):
    """Replay the TestRunner meta guard: every pinned 0.9.N must be the release."""
    pinned = set()
    for line in text.split("\n"):
        if ("<Version>0.9." not in line
                and "Classroom Studio v0.9." not in line
                and "BundleVersion" not in line):
            continue
        for m in re.finditer(r"0\.9\.(\d+)", line):
            i = m.start()
            is_label = (i > 0 and line[i - 1] == "v"
                        and m.end() < len(line) and line[m.end()] == ":")
            if not is_label:
                pinned.add(int(m.group(1)))
    return pinned


cache = {}
for path, old, new, _min in EDITS:
    if path not in cache:
        cache[path] = pathlib.Path(path).read_text(encoding="utf-8")

changed = {}
problems = []
for path, old, new, minimum in EDITS:
    text = cache[path]
    hits = text.count(old)
    if hits == 0 and text.count(new) > 0:
        print("ok    already patched: %s -> %s" % (path.split("/")[-1], new))
        continue
    if hits < minimum:
        problems.append("%s: expected at least %d of %r, found %d" % (path, minimum, old, hits))
        continue
    cache[path] = text.replace(old, new)
    changed[path] = True
    print("edit  %s: %r -> %r  x%d" % (path.split("/")[-1], old, new, hits))

if problems:
    print("ABORTING, unexpected source shape:")
    for p in problems:
        print("  " + p)
    sys.exit(1)

for path in changed:
    pathlib.Path(path).write_text(cache[path], encoding="utf-8")

# post-conditions -----------------------------------------------------------
exporter = pathlib.Path(EXPORTER).read_text(encoding="utf-8")
if ('BundleVersion = "' + BUNDLE + '"') not in exporter:
    print("FAIL: PicoFirmwareExporter.BundleVersion is not " + BUNDLE)
    sys.exit(1)

runner = pathlib.Path(RUNNER).read_text(encoding="utf-8")
pins = meta_pins(runner)
if pins != set([64]):
    print("FAIL: TestRunner still pins these releases: " + repr(sorted(pins)))
    sys.exit(1)

csproj = pathlib.Path(CSPROJ).read_text(encoding="utf-8")
vm = pathlib.Path(VM).read_text(encoding="utf-8")
if ("<Version>" + APP + "</Version>") not in csproj or ("Classroom Studio v" + APP) not in vm:
    print("FAIL: csproj or banner did not land on " + APP)
    sys.exit(1)

print("PASS: app " + APP + ", bundle " + BUNDLE + ", TestRunner pins = {64}")
