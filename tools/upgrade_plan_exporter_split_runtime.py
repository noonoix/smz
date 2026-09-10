#!/usr/bin/env python3
"""Migrate the PLAN|2 exporter to the hardware-proven three-file split runtime.

Idempotent. Edits the canonical exporter template and C# test payload; the
checked-in PlanExporter.cs/TestRunner.cs remain generated outputs.
"""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
TPL = ROOT / "tools" / "PlanExporter.cs.tpl"
TEST = ROOT / "tools" / "plan_exporter_test_step.cs.inc"
MARKER = "PLAN2_SPLIT_RUNTIME_MIGRATION"


def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: anchor count {count}, expected 1")
    return text.replace(old, new, 1)


s = TPL.read_text(encoding="utf-8")
if MARKER not in s:
    s = once(s, "// PLAN2_BUNDLE_MIGRATION", "// PLAN2_BUNDLE_MIGRATION\n// " + MARKER, "template marker")
    s = once(s,
        '        var enginePath = Path.Combine(dir, "plan_engine.py");\n        var readmePath = Path.Combine(dir, "README-PLAN.md");',
        '        var enginePath = Path.Combine(dir, "plan_engine.py");\n        var motionPath = Path.Combine(dir, "plan_motion.py");\n        var typingPath = Path.Combine(dir, "plan_typing.py");\n        var readmePath = Path.Combine(dir, "README-PLAN.md");',
        "runtime paths")
    s = once(s,
        '        payloads.Add((enginePath, BuildEnginePy()));\n        payloads.Add((readmePath, BuildReadme(bundle.Root, Path.GetFileName(sourceName), machine)));',
        '        payloads.Add((enginePath, BuildEnginePy()));\n        payloads.Add((motionPath, BuildMotionPy()));\n        payloads.Add((typingPath, BuildTypingPy()));\n        payloads.Add((readmePath, BuildReadme(bundle.Root, Path.GetFileName(sourceName), machine)));',
        "runtime payloads")
    s = once(s,
        '    public static string BuildEnginePy() => EngineTemplate.Replace("\\r\\n", "\\n");',
        '    public static string BuildEnginePy() => EngineTemplate.Replace("\\r\\n", "\\n");\n    public static string BuildMotionPy() => MotionTemplate.Replace("\\r\\n", "\\n");\n    public static string BuildTypingPy() => TypingTemplate.Replace("\\r\\n", "\\n");',
        "runtime builders")
    s = once(s,
        '        sb.Append("- plan_engine.py ← موتور PLAN|2 (فقط وقتی نسخه‌ی فریم‌ور عوض شود دوباره لازم است)\\n\\n");',
        '        sb.Append("- plan_engine.py + plan_motion.py + plan_typing.py ← runtime کامل کم‌حافظه‌ی PLAN|2\\n\\n");',
        "readme runtime list")
    s = once(s,
        '    // The PLAN|2 engine (portable/plan3/CIRCUITPY/plan_engine.py) is spliced in here by\n    // tools/make_plan_exporter.py as a 4-quote raw string (the engine holds docstrings).\n    // TestRunner compares the embedded copy byte-for-byte against the repo golden\n    // (modulo line endings), so the template can never drift from the firmware line it targets.\n    private const string EngineTemplate = __ENGINE_TEMPLATE__;',
        '    // Hardware-proven split runtime. Generated from the canonical engine; do not hand-edit.\n    private const string EngineTemplate = __ENGINE_CORE_TEMPLATE__;\n    private const string MotionTemplate = __ENGINE_MOTION_TEMPLATE__;\n    private const string TypingTemplate = __ENGINE_TYPING_TEMPLATE__;',
        "runtime template markers")
    s = s.replace("plan_engine.py (the PLAN|2 engine)", "plan_engine.py + plan_motion.py + plan_typing.py (the split PLAN|2 runtime)")
    s = s.replace("every root/child/engine/readme payload", "every root/child/runtime/readme payload")
    TPL.write_text(s, encoding="utf-8", newline="\n")
    print("PLAN2 split-runtime template migration applied")
else:
    print("PLAN2 split-runtime template migration already applied")

t = TEST.read_text(encoding="utf-8")
if MARKER not in t:
    t = once(t, "// PLAN2_BUNDLE_TESTS", "// PLAN2_BUNDLE_TESTS\n            // " + MARKER, "test marker")
    t = once(t,
        'Assert(bundleWritten.Count == 6 && new[] { "plan.txt", "child1.txt", "child2.txt", "grand.txt", "plan_engine.py", "README-PLAN.md" }.All(n => File.Exists(Path.Combine(outDir, n))),',
        'Assert(bundleWritten.Count == 8 && new[] { "plan.txt", "child1.txt", "child2.txt", "grand.txt", "plan_engine.py", "plan_motion.py", "plan_typing.py", "README-PLAN.md" }.All(n => File.Exists(Path.Combine(outDir, n))),',
        "recursive bundle count")
    t = once(t,
        '                File.WriteAllText(Path.Combine(rollbackOut, "plan_engine.py"), "OLD ENGINE");\n                File.WriteAllText(Path.Combine(rollbackOut, "README-PLAN.md"), "OLD README");',
        '                File.WriteAllText(Path.Combine(rollbackOut, "plan_engine.py"), "OLD ENGINE");\n                File.WriteAllText(Path.Combine(rollbackOut, "plan_motion.py"), "OLD MOTION");\n                File.WriteAllText(Path.Combine(rollbackOut, "plan_typing.py"), "OLD TYPING");\n                File.WriteAllText(Path.Combine(rollbackOut, "README-PLAN.md"), "OLD README");',
        "rollback setup")
    t = once(t,
        '                       File.ReadAllText(Path.Combine(rollbackOut, "plan_engine.py")) == "OLD ENGINE" &&\n                       File.ReadAllText(Path.Combine(rollbackOut, "README-PLAN.md")) == "OLD README",',
        '                       File.ReadAllText(Path.Combine(rollbackOut, "plan_engine.py")) == "OLD ENGINE" &&\n                       File.ReadAllText(Path.Combine(rollbackOut, "plan_motion.py")) == "OLD MOTION" &&\n                       File.ReadAllText(Path.Combine(rollbackOut, "plan_typing.py")) == "OLD TYPING" &&\n                       File.ReadAllText(Path.Combine(rollbackOut, "README-PLAN.md")) == "OLD README",',
        "rollback assertion")
    old_gold = '''            // the embedded engine is the on-drive gen-1 engine, byte for byte
            var pexEngineOnDisk = PexReadRepo(Path.Combine("portable", "plan3", "CIRCUITPY", "plan_engine.py"));
            Assert(pexEngineOnDisk is not null,
                "v0.9.65: firmware/code64b/plan_engine.py found next to the repo for the golden compare");
            Assert(pexEngineOnDisk is not null && PexNormEol(pexEngineOnDisk!) == PexNormEol(PlanExporter.BuildEnginePy()),
                "v0.9.65: the embedded plan engine is byte-identical to firmware/code64b/plan_engine.py");'''
    new_gold = '''            // all three embedded runtime modules are byte-identical to generated split goldens
            var pexEngineOnDisk = PexReadRepo(Path.Combine("portable", "plan3", "CIRCUITPY-SPLIT", "plan_engine.py"));
            var pexMotionOnDisk = PexReadRepo(Path.Combine("portable", "plan3", "CIRCUITPY-SPLIT", "plan_motion.py"));
            var pexTypingOnDisk = PexReadRepo(Path.Combine("portable", "plan3", "CIRCUITPY-SPLIT", "plan_typing.py"));
            Assert(pexEngineOnDisk is not null && pexMotionOnDisk is not null && pexTypingOnDisk is not null,
                "v0.9.66: all generated split runtime modules found for golden compare");
            Assert(PexNormEol(pexEngineOnDisk!) == PexNormEol(PlanExporter.BuildEnginePy()) &&
                   PexNormEol(pexMotionOnDisk!) == PexNormEol(PlanExporter.BuildMotionPy()) &&
                   PexNormEol(pexTypingOnDisk!) == PexNormEol(PlanExporter.BuildTypingPy()),
                "v0.9.66: all embedded split runtime modules are byte-identical to generated goldens");'''
    t = once(t, old_gold, new_gold, "embedded runtime golden")
    t = once(t,
        'Assert(pexWritten.Count == 3 && File.Exists(Path.Combine(pexTmp, "plan.txt"))\n                       && File.Exists(Path.Combine(pexTmp, "plan_engine.py")) && File.Exists(Path.Combine(pexTmp, "README-PLAN.md")),',
        'Assert(pexWritten.Count == 5 && File.Exists(Path.Combine(pexTmp, "plan.txt"))\n                       && File.Exists(Path.Combine(pexTmp, "plan_engine.py"))\n                       && File.Exists(Path.Combine(pexTmp, "plan_motion.py"))\n                       && File.Exists(Path.Combine(pexTmp, "plan_typing.py"))\n                       && File.Exists(Path.Combine(pexTmp, "README-PLAN.md")),',
        "simple export count")
    t = once(t,
        '                       && File.ReadAllText(Path.Combine(pexTmp, "plan_engine.py")).Contains("def parse_plan"),',
        '                       && File.ReadAllText(Path.Combine(pexTmp, "plan_engine.py")).Contains("def parse_plan")\n                       && File.ReadAllText(Path.Combine(pexTmp, "plan_motion.py")).Contains("def _exec_rmouse")\n                       && File.ReadAllText(Path.Combine(pexTmp, "plan_typing.py")).Contains("def plan_typing"),',
        "simple export contents")
    TEST.write_text(t, encoding="utf-8", newline="\n")
    print("PLAN2 split-runtime C# tests applied")
else:
    print("PLAN2 split-runtime C# tests already applied")
