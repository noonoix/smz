#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_plan_exporter_ui.py - v0.9.65 wiring patcher (phase 2 of the portable line).

Applies the three anchored, idempotent edits that wire PlanExporter into the app:

  1. tests/TestRunner.cs   <- inserts the step-59 block (tools/plan_exporter_test_step.cs.inc)
                              before the '=== Results' print (59 pins the PLAN|1 contract).
  2. MainViewModel.cs      <- inserts the ExportPicoPlan command
                              (tools/plan_exporter_vm_command.cs.inc) before UpdateFileText().
  3. MainWindow.xaml       <- adds File -> 'Export Pico Plan... (plan.txt)' right after
                              the Export Pico Firmware item.

NO version pins are touched (the release-cut bump is tools/patch_version_pins_0965.py):
the meta guard only scans <Version>0.9.* / 'Classroom Studio v0.9.*' / BundleVersion lines,
and step-59's assertion labels (v0.9.65:) are explicitly excluded from its pin scan.

Idempotent: a second run finds every marker present and exits 0 without edits.
Usage: python tools/patch_plan_exporter_ui.py [repo root]
Exit: 0 = applied/already, 1 = unexpected source shape (nothing half-written).
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(".").resolve()
XAML = ROOT / "ams-shell" / "src" / "Ams.UI" / "MainWindow.xaml"
VM = ROOT / "ams-shell" / "src" / "Ams.UI" / "ViewModels" / "MainViewModel.cs"
RUNNER = ROOT / "tests" / "TestRunner.cs"
INC_TEST = ROOT / "tools" / "plan_exporter_test_step.cs.inc"
INC_VM = ROOT / "tools" / "plan_exporter_vm_command.cs.inc"

RESULTS_ANCHOR = '        Console.WriteLine($"=== Results: {passed} passed, {failed} failed ===");'
VM_ANCHOR = "    private void UpdateFileText()"
XAML_ANCHOR = ('                <MenuItem Header="Export _Pico Firmware… (per system)" Command="{Binding ExportPicoFirmwareCommand}"\n'
               '                          ToolTip="خروجی CircuitPython برای رزبری پای پیکو — یک‌بار در هر سیستم" />')
XAML_ITEM = ('                <MenuItem Header="Export Pico _Plan… (plan.txt)" Command="{Binding ExportPicoPlanCommand}"\n'
             '                          ToolTip="خروجی plan.txt پرتابل برای پیکو — موتور gen-1 فریم‌ور 0.9.64b" />')

MARK_TEST = "Step 59: v0.9.65 plan exporter"
MARK_VM = "private void ExportPicoPlan()"
MARK_XAML = "ExportPicoPlanCommand"

problems = []
changed = []
orig_texts = {}   # path -> content BEFORE any edit (the balance check is a DELTA, never absolute:
                  # the baseline file can carry characters the naive stripper miscounts)


def load(p):
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:
        problems.append("cannot read %s: %s" % (p, exc))
        return None


def save(p, text):
    p.write_text(text, encoding="utf-8")


# -- capture pristine copies up front (delta baseline for the balance check) -----------
for _p in (RUNNER, VM):
    if _p.exists():
        orig_texts[_p] = _p.read_text(encoding="utf-8")


# -- precondition: the payload files exist -------------------------------------------
for p in (INC_TEST, INC_VM):
    if not p.exists():
        problems.append("missing payload: %s" % p)
if problems:
    print("ABORTING:")
    for p in problems:
        print("  " + p)
    sys.exit(1)

# -- 1) TestRunner.cs -----------------------------------------------------------------
text = load(RUNNER)
if text is not None:
    if MARK_TEST in text:
        print("ok    already patched: tests/TestRunner.cs (step 59)")
    else:
        if text.count(RESULTS_ANCHOR) != 1:
            problems.append("TestRunner.cs: Results anchor found %d times (want 1)" % text.count(RESULTS_ANCHOR))
        else:
            block = INC_TEST.read_text(encoding="utf-8")
            text = text.replace(RESULTS_ANCHOR, block + RESULTS_ANCHOR)
            save(RUNNER, text)
            changed.append("tests/TestRunner.cs")
            print("edit  TestRunner.cs: step 59 inserted before the Results print")

# -- 2) MainViewModel.cs ---------------------------------------------------------------
text = load(VM)
if text is not None:
    if MARK_VM in text:
        print("ok    already patched: MainViewModel.cs (ExportPicoPlan)")
    else:
        if text.count(VM_ANCHOR) != 1:
            problems.append("MainViewModel.cs: UpdateFileText anchor found %d times (want 1)" % text.count(VM_ANCHOR))
        else:
            block = INC_VM.read_text(encoding="utf-8")
            text = text.replace(VM_ANCHOR, block + VM_ANCHOR)
            save(VM, text)
            changed.append("MainViewModel.cs")
            print("edit  MainViewModel.cs: ExportPicoPlan command inserted before UpdateFileText")

# -- 3) MainWindow.xaml -----------------------------------------------------------------
text = load(XAML)
if text is not None:
    if MARK_XAML in text:
        print("ok    already patched: MainWindow.xaml (menu item)")
    else:
        if text.count(XAML_ANCHOR) != 1:
            problems.append("MainWindow.xaml: firmware menu anchor found %d times (want 1)" % text.count(XAML_ANCHOR))
        else:
            text = text.replace(XAML_ANCHOR, XAML_ANCHOR + "\n" + XAML_ITEM)
            save(XAML, text)
            changed.append("MainWindow.xaml")
            print("edit  MainWindow.xaml: Export Pico Plan menu item added after the firmware item")

if problems:
    print("ABORTING, unexpected source shape (no partial writes done for failed files):")
    for p in problems:
        print("  " + p)
    sys.exit(1)

# -- post-conditions --------------------------------------------------------------------
runner = RUNNER.read_text(encoding="utf-8")
vm = VM.read_text(encoding="utf-8")
xaml = XAML.read_text(encoding="utf-8")
for name, text, needles in (
    ("tests/TestRunner.cs", runner, [MARK_TEST, RESULTS_ANCHOR,
                                     "PlanExporter.Compile", "PlanExporter.Export(",
                                     "PlanBlockedException", "BuildEnginePy()",
                                     "plan_engine.py", "WLIGHT|1200,1300,500,9000,1"]),
    ("MainViewModel.cs", vm, [MARK_VM, VM_ANCHOR, "PlanExporter.Export(", "PlanBlockedException"]),
    ("MainWindow.xaml", xaml, [MARK_XAML, "ExportPicoFirmwareCommand"]),
):
    for n in needles:
        if n not in text:
            problems.append("post-check failed: %s lost %r" % (name, n))

# the xaml must still parse as XML after the edit
import xml.etree.ElementTree as ET
try:
    ET.fromstring(xaml)
except Exception as exc:
    problems.append("MainWindow.xaml is not well-formed XML after the edit: %s" % exc)

# balance check on the two edited C# files (code-only: strings/comments stripped)
import re

def strip_code(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r'@"(?:[^"]|"")*"', '""', src)
    src = re.sub(r'\$"(?:[^"\\]|\\.)*"', '""', src)
    src = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)
    src = re.sub(r"'(?:[^'\\]|\\.)'", "''", src)
    return src

for name, path in (("tests/TestRunner.cs", RUNNER), ("MainViewModel.cs", VM)):
    before = strip_code(orig_texts.get(path, ""))
    after = strip_code(path.read_text(encoding="utf-8"))
    for a, b in (("{", "}"), ("(", ")"), ("[", "]")):
        # DELTA, never absolute: the added block must be self-balanced relative to the baseline
        if (after.count(a) - after.count(b)) != (before.count(a) - before.count(b)):
            problems.append("%s: the edit shifted the %s%s balance (baseline %d vs %d, now %d vs %d)"
                            % (name, a, b, before.count(a), before.count(b),
                               after.count(a), after.count(b)))

if problems:
    print("ABORTING on post-conditions (files were already written - inspect before committing):")
    for p in problems:
        print("  " + p)
    sys.exit(1)

print("PASS: plan-exporter UI wiring applied to %d file(s) (idempotent on re-run)" % len(changed))
