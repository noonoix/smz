#!/usr/bin/env python3
"""Temporary helper: dump the version-pin context needed to fix CI run #19.

Writes reports/pin-report.txt with:
  A) version-constant definitions inside tests/TestRunner.cs
  B) every line containing 0.9.60 (capped)
  C) context blocks around each failing test title
  D) the pin lines in csproj / MainViewModel / PicoFirmwareExporter
"""
import pathlib
import re

ROOT = pathlib.Path(".")
out = []


def add(line=""):
    out.append(line)


def trim(s, n=150):
    s = s.rstrip()
    return s if len(s) <= n else s[:n] + " ..."


tr = ROOT / "tests/TestRunner.cs"
lines = tr.read_text(encoding="utf-8", errors="replace").split("\n")
add("# tests/TestRunner.cs total lines: %d" % len(lines))

add("")
add("=== A) VERSION CONSTANT DEFINITIONS ===")
pat = re.compile(r"(const|static|readonly|var|string)\s+\w*[Vv]ersion\w*\s*=")
for i, l in enumerate(lines):
    if pat.search(l):
        add("%d: %s" % (i + 1, trim(l.strip())))

add("")
add("=== B) LINES CONTAINING 0.9.60 ===")
hits = [(i + 1, l.strip()) for i, l in enumerate(lines) if "0.9.60" in l]
add("count=%d" % len(hits))
for n, l in hits[:150]:
    add("%d: %s" % (n, trim(l, 140)))

titles = [
    "app version, banner and Pico bundle version match",
    "version pins for this release",
    "BundleVersion is 0.9.60",
    "version pins (firmware bundle, csproj, app banner)",
    "fully baked with the fixed control contract",
    "all version pins match current release",
]
add("")
add("=== C) CONTEXT BLOCKS ===")
for t in titles:
    idxs = [i for i, l in enumerate(lines) if t in l]
    add("")
    add("--- title: %s (matches=%d) ---" % (t, len(idxs)))
    for i in idxs[:1]:
        s = max(0, i - 14)
        e = min(len(lines), i + 12)
        for j in range(s, e):
            add("%d: %s" % (j + 1, trim(lines[j], 150)))

others = [
    ("ams-shell/src/Ams.UI/Ams.UI.csproj", ["<Version>"]),
    ("ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs", ["Classroom Studio v0.9", "v0.9.6"]),
    ("ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs", ["BundleVersion"]),
]
add("")
add("=== D) PIN LINES IN SOURCE FILES ===")
for path, pats in others:
    p = ROOT / path
    add("")
    add("--- %s ---" % path)
    if not p.exists():
        add("MISSING")
        continue
    fl = p.read_text(encoding="utf-8", errors="replace").split("\n")
    shown = 0
    for i, l in enumerate(fl):
        if any(x in l for x in pats):
            add("%d: %s" % (i + 1, trim(l.strip(), 150)))
            shown += 1
            if shown >= 12:
                add("... (more matches omitted)")
                break

rep = ROOT / "reports"
rep.mkdir(exist_ok=True)
(rep / "pin-report.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote reports/pin-report.txt with %d lines" % len(out))
