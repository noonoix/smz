#!/usr/bin/env python3
"""Bump the Classroom Studio release pins: app 0.9.64 -> 0.9.65 (the PlanExporter release).

DO NOT run on a feature branch - this is the RELEASE-CUT tool (run it right before the
release merge, on the release branch). The feature branch feat/plan-exporter-plan1 lands
without any version bump (the proven PR #13/#16 rhythm).

Why the meta guard changes shape here: v0.9.65 adds the plan exporter but does NOT touch
the Pico firmware template, so PicoFirmwareExporter.BundleVersion honestly stays "0.9.64f"
(the exported code.py stays byte-identical to the golden firmware/code64b/code64b.py).
Until now the guard demanded app-minor == bundle-minor; this patch teaches it the split:
pins on BundleVersion lines must equal curBundleMinor (64), every other pin must equal
curMinor (65).

Idempotent: a second run finds nothing to do and still exits 0.
"""
import pathlib
import re
import sys

APP_OLD = "0.9.64"
APP = "0.9.65"
BUNDLE = "0.9.64f"          # unchanged on purpose - the firmware template stays on the accepted 0.9.64f line
BS = chr(92)

CSPROJ = "ams-shell/src/Ams.UI/Ams.UI.csproj"
VM = "ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs"
EXPORTER = "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
RUNNER = "tests/TestRunner.cs"

# (file, old, new, minimum expected occurrences)
EDITS = [
    (CSPROJ, "<Version>" + APP_OLD + "</Version>", "<Version>" + APP + "</Version>", 1),
    (VM, "Classroom Studio v" + APP_OLD, "Classroom Studio v" + APP, 1),
    (RUNNER, "<Version>" + APP_OLD + "</Version>", "<Version>" + APP + "</Version>", 20),
    (RUNNER, "Classroom Studio v" + APP_OLD, "Classroom Studio v" + APP, 15),
    (RUNNER, "csproj version is " + APP_OLD, "csproj version is " + APP, 2),
    # the meta guard learns the app/bundle split (firmware stays on the accepted 0.9.64f line -> bundle stays on 0.9.64f)
    (RUNNER, "        var pinned = new List<int>();",
             "        var pinned = new List<int>();\n"
             "        var pinnedBundle = new List<int>();   // bundle pins are tracked apart: the firmware template may stay on an older line",
             1),
    (RUNNER, "                if (!isLabel) pinned.Add(int.Parse(metaMatch.Groups[1].Value));",
             "                if (!isLabel) (metaLine.Contains(\"BundleVersion\") ? pinnedBundle : pinned).Add(int.Parse(metaMatch.Groups[1].Value));",
             1),
    (RUNNER, "        var curMinor = 64;",
             "        var curMinor = 65;\n"
             "        var curBundleMinor = 64;   // the firmware template is unchanged in this release, so the bundle stays on its older line",
             1),
    (RUNNER, "        Assert(pinned.Count > 0 && pinned.Distinct().All(n => n == curMinor),\n"
             "            $\"v0.9.58: all version pins match current release 0.9.{curMinor} (found: {pinnedText})\");",
             "        Assert(pinned.Count > 0 && pinned.Distinct().All(n => n == curMinor),\n"
             "            $\"v0.9.58: all app version pins match current release 0.9.{curMinor} (found: {pinnedText})\");\n"
             "        var pinnedBundleText = string.Join(\", \", pinnedBundle.Distinct().OrderBy(n => n));\n"
             "        Assert(pinnedBundle.Count > 0 && pinnedBundle.Distinct().All(n => n == curBundleMinor),\n"
             "            $\"v0.9.58: all bundle pins stay on the untouched firmware line 0.9.{curBundleMinor}b (found: {pinnedBundleText})\");",
             1),
]


def meta_pins(text):
    """Replay the NEW TestRunner meta guard: app pins must be 65, bundle pins 64."""
    app, bundle = set(), set()
    for line in text.split("\n"):
        is_bundle = "BundleVersion" in line
        if ("<Version>0.9." not in line and "Classroom Studio v0.9." not in line and not is_bundle):
            continue
        for m in re.finditer(r"0\.9\.(\d+)", line):
            i = m.start()
            is_label = (i > 0 and line[i - 1] == "v"
                        and m.end() < len(line) and line[m.end()] == ":")
            if not is_label:
                (bundle if is_bundle else app).add(int(m.group(1)))
    return app, bundle


cache = {}
for path, old, new, _min in EDITS:
    if path not in cache:
        cache[path] = pathlib.Path(path).read_text(encoding="utf-8")

changed = {}
problems = []
for path, old, new, minimum in EDITS:
    text = cache[path]
    hits = text.count(old)
    # already-applied detection: for normal edits the old text is gone; for prefix-extension
    # edits (new = old + appended lines) the old text SURVIVES inside the new, so the applied
    # marker is the presence of the new text, not the absence of the old.
    if text.count(new) > 0 and (hits == 0 or old in new):
        print("ok    already patched: %s -> %s" % (path.split("/")[-1], new.split(chr(10))[0][:60]))
        continue
    if hits < minimum:
        problems.append("%s: expected at least %d of %r, found %d" % (path, minimum, old[:70], hits))
        continue
    cache[path] = text.replace(old, new)
    changed[path] = True
    print("edit  %s: %r -> %r  x%d" % (path.split("/")[-1], old[:60], new[:60], hits))

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
    print("FAIL: PicoFirmwareExporter.BundleVersion moved - the firmware template stays on the accepted 0.9.64f line in v0.9.65")
    sys.exit(1)

runner = pathlib.Path(RUNNER).read_text(encoding="utf-8")
app_pins, bundle_pins = meta_pins(runner)
if app_pins != set([65]) or bundle_pins != set([64]):
    print("FAIL: pin families wrong after the bump: app=%r bundle=%r" % (sorted(app_pins), sorted(bundle_pins)))
    sys.exit(1)
if runner.count("var pinnedBundle = new List<int>();") != 1:
    print("FAIL: the meta-guard edit is not unique/idempotent (pinnedBundle declared %d times)"
          % runner.count("var pinnedBundle = new List<int>();"))
    sys.exit(1)

csproj = pathlib.Path(CSPROJ).read_text(encoding="utf-8")
vm = pathlib.Path(VM).read_text(encoding="utf-8")
if ("<Version>" + APP + "</Version>") not in csproj or ("Classroom Studio v" + APP) not in vm:
    print("FAIL: csproj or banner did not land on " + APP)
    sys.exit(1)

print("PASS: app " + APP + ", bundle stays " + BUNDLE + ", TestRunner pins app={65} bundle={64}")
