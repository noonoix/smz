#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "tools/PlanExporter.cs.tpl"
TEST = ROOT / "tools/plan_exporter_test_step.cs.inc"
GEN = ROOT / "tools/make_plan_exporter.py"


def replace(path, old, new, count=None):
    s = path.read_text(encoding="utf-8")
    n = s.count(old)
    want = 1 if count is None else count
    if n != want:
        raise SystemExit(f"guard failed: {path}: expected {want} matches, got {n}: {old[:80]!r}")
    path.write_text(s.replace(old, new), encoding="utf-8", newline="\n")

# Pin the single engine source of truth to the verified PLAN|2 runtime.
replace(GEN, 'tools/PlanExporter.cs.tpl + firmware/code64b/plan_engine.py (the gen-1 plan engine,',
             'tools/PlanExporter.cs.tpl + portable/plan3/CIRCUITPY/plan_engine.py (the PLAN|2 engine,')
replace(GEN, 'ENGINE = ROOT / "firmware" / "code64b" / "plan_engine.py"',
             'ENGINE = ROOT / "portable" / "plan3" / "CIRCUITPY" / "plan_engine.py"')
replace(GEN, 'problems.append("firmware/code64b/plan_engine.py lost its header - wrong file?")',
             'problems.append("portable/plan3/CIRCUITPY/plan_engine.py lost its header - wrong file?")')
replace(GEN, 'round trip: byte-identical to firmware/code64b/plan_engine.py',
             'round trip: byte-identical to portable/plan3/CIRCUITPY/plan_engine.py')

# Stage 1: PLAN|2 header + exact PLAN|2 runtime. Action parity is added in the next guarded patch.
replace(TPL, 'public const int PlanFormatVersion = 1;', 'public const int PlanFormatVersion = 2;')
replace(TPL, 'public const string EngineVersion = "0.9.64b";', 'public const string EngineVersion = "0.9.66";')
replace(TPL, 'sb.Append("PLAN|1\\n");', 'sb.Append("PLAN|2\\n");')
replace(TPL, 'fields[1] != "1") Bad("PLAN must be first with version 1")',
             'fields[1] != "2") Bad("PLAN must be first with version 2")')
replace(TPL, 'The gen-1 plan engine (firmware/code64b/plan_engine.py) is spliced in here by',
             'The PLAN|2 engine (portable/plan3/CIRCUITPY/plan_engine.py) is spliced in here by')
replace(TPL, 'The gen-1 plan engine, embedded verbatim (firmware/code64b/plan_engine.py).',
             'The PLAN|2 plan engine, embedded verbatim (portable/plan3/CIRCUITPY/plan_engine.py).')
replace(TPL, '# راهنمای پلن پرتابل پیکو (PLAN|1 - فریم‌ور 0.9.64b)',
             '# راهنمای پلن پرتابل پیکو (PLAN|2 - فریم‌ور 0.9.66)')

# Atomic bundle publish: validate/prepare everything before replacing any destination.
old = '''        var written = new List<string> { full };
        File.WriteAllText(full, result.Text);
        var enginePath = Path.Combine(dir, "plan_engine.py");
        File.WriteAllText(enginePath, BuildEnginePy());
        written.Add(enginePath);
        var readmePath = Path.Combine(dir, "README-PLAN.md");
        File.WriteAllText(readmePath, BuildReadme(result, sourceName, machine));
        written.Add(readmePath);
        return written;'''
new = '''        var enginePath = Path.Combine(dir, "plan_engine.py");
        var readmePath = Path.Combine(dir, "README-PLAN.md");
        var payloads = new (string Path, string Text)[]
        {
            (full, result.Text),
            (enginePath, BuildEnginePy()),
            (readmePath, BuildReadme(result, sourceName, machine)),
        };
        var tx = Guid.NewGuid().ToString("N");
        var temps = payloads.Select(p => p.Path + "." + tx + ".tmp").ToArray();
        var backups = payloads.Select(p => p.Path + "." + tx + ".bak").ToArray();
        var published = new List<int>();
        try
        {
            // No destination is touched until every complete file is safely staged.
            for (int i = 0; i < payloads.Length; i++)
                File.WriteAllText(temps[i], payloads[i].Text, new UTF8Encoding(false));
            for (int i = 0; i < payloads.Length; i++)
            {
                if (File.Exists(payloads[i].Path)) File.Move(payloads[i].Path, backups[i]);
                File.Move(temps[i], payloads[i].Path);
                published.Add(i);
            }
            foreach (var b in backups) if (File.Exists(b)) File.Delete(b);
            return payloads.Select(p => p.Path).ToList();
        }
        catch
        {
            // Best-effort rollback: a failed export never leaves a mixed old/new bundle.
            foreach (var i in published.AsEnumerable().Reverse())
                if (File.Exists(payloads[i].Path)) File.Delete(payloads[i].Path);
            for (int i = 0; i < payloads.Length; i++)
                if (File.Exists(backups[i])) File.Move(backups[i], payloads[i].Path, true);
            throw;
        }
        finally
        {
            foreach (var p in temps.Concat(backups))
                if (File.Exists(p)) File.Delete(p);
        }'''
replace(TPL, old, new)

# Keep the generated TestRunner block aligned with stage 1 without weakening blockers.
s = TEST.read_text(encoding="utf-8")
s = s.replace('PLAN|1', 'PLAN|2')
s = s.replace('firmware", "code64b", "plan_engine.py', 'portable", "plan3", "CIRCUITPY", "plan_engine.py')
s = s.replace('PlanExporter.EngineVersion == PicoFirmwareExporter.BundleVersion',
              'PlanExporter.EngineVersion == "0.9.66"')
TEST.write_text(s, encoding="utf-8", newline="\n")
print("PLAN2 stage-1 anchors applied")
