#!/usr/bin/env python3
"""Add deterministic PLAN|2 recursive-bundle/typed-validator/rollback tests."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
p = root / "tools" / "plan_exporter_test_step.cs.inc"
s = p.read_text(encoding="utf-8")
marker = "PLAN2_BUNDLE_TESTS"
if marker in s:
    print("PLAN2 recursive-bundle tests already applied")
    raise SystemExit(0)

anchor = "            // the embedded engine is the on-drive gen-1 engine, byte for byte"
if s.count(anchor) != 1:
    raise SystemExit("bundle-test insertion anchor not found exactly once")

block = r'''            // PLAN2_BUNDLE_TESTS — recursive compile is a preflighted, all-or-nothing bundle.
            var pexBundleTmp = Path.Combine(Path.GetTempPath(), "pex_bundle_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(pexBundleTmp);
            try
            {
                var srcDir = Path.Combine(pexBundleTmp, "src");
                var outDir = Path.Combine(pexBundleTmp, "out");
                Directory.CreateDirectory(srcDir); Directory.CreateDirectory(outDir);
                var rootPath = Path.Combine(srcDir, "root.amsj");
                var grandPath = Path.Combine(srcDir, "grand.amsj");
                var child1Path = Path.Combine(srcDir, "child1.amsj");
                var child2Path = Path.Combine(srcDir, "child2.amsj");
                DocumentService.Save(grandPath, new[] { PexStep("mouseClick") });
                DocumentService.Save(child1Path, new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "grand.amsj" }) });
                DocumentService.Save(child2Path, new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "grand.amsj" }) });
                var rootBundle = new List<StepNode>
                {
                    PexStep("playScript", new Dictionary<string, object?> { ["path"] = "child1.amsj" }),
                    PexStep("playScript", new Dictionary<string, object?> { ["path"] = "child2.amsj" }),
                };
                DocumentService.Save(rootPath, rootBundle);
                var bundleWritten = PlanExporter.Export(Path.Combine(outDir, "plan.txt"), rootBundle,
                    pexSettings, 1920, 1080, rootPath, "TESTPC");
                Assert(bundleWritten.Count == 6 && new[] { "plan.txt", "child1.txt", "child2.txt", "grand.txt", "plan_engine.py", "README-PLAN.md" }.All(n => File.Exists(Path.Combine(outDir, n))),
                    "v0.9.66: recursive playScript exports root + every child + engine/readme");
                Assert(bundleWritten.Count(f => Path.GetFileName(f).Equals("grand.txt", StringComparison.OrdinalIgnoreCase)) == 1,
                    "v0.9.66: duplicate reference to one child source emits one plan file");
                Assert(File.ReadAllText(Path.Combine(outDir, "child1.txt")).Contains("INCLUDE|file=grand.txt"),
                    "v0.9.66: child plans keep recursive INCLUDE links");

                // Same output basename from two different source paths is ambiguous and must block.
                var oneDir = Path.Combine(srcDir, "one"); var twoDir = Path.Combine(srcDir, "two");
                Directory.CreateDirectory(oneDir); Directory.CreateDirectory(twoDir);
                DocumentService.Save(Path.Combine(oneDir, "same.amsj"), new[] { PexStep("mouseClick") });
                DocumentService.Save(Path.Combine(twoDir, "same.amsj"), new[] { PexStep("delay") });
                var collision = new List<StepNode>
                {
                    PexStep("playScript", new Dictionary<string, object?> { ["path"] = Path.Combine("one", "same.amsj") }),
                    PexStep("playScript", new Dictionary<string, object?> { ["path"] = Path.Combine("two", "same.amsj") }),
                };
                try { PlanExporter.Export(Path.Combine(outDir, "collision-root.txt"), collision, pexSettings, 1920, 1080, rootPath, "TESTPC"); Assert(false, "v0.9.66: duplicate include output must block"); }
                catch (PlanExporter.PlanBlockedException bx) { Assert(bx.Errors.Any(e => e.Contains("duplicate include output")), "v0.9.66: duplicate output-name guard is explicit"); }

                // Missing nested file is found during preflight, before any destination write.
                var missingChild = Path.Combine(srcDir, "missing-child.amsj");
                DocumentService.Save(missingChild, new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "nope.amsj" }) });
                var missingOut = Path.Combine(pexBundleTmp, "missing-out"); Directory.CreateDirectory(missingOut);
                try { PlanExporter.Export(Path.Combine(missingOut, "plan.txt"), new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "missing-child.amsj" }) }, pexSettings, 1920, 1080, rootPath, "TESTPC"); Assert(false, "v0.9.66: nested missing include must block"); }
                catch (PlanExporter.PlanBlockedException bx) { Assert(bx.Errors.Any(e => e.Contains("child not found")), "v0.9.66: nested missing-file guard fires in preflight"); }
                Assert(!Directory.EnumerateFileSystemEntries(missingOut).Any(), "v0.9.66: failed include preflight writes zero files");

                // Cycle A -> B -> A is rejected, not silently skipped.
                var aPath = Path.Combine(srcDir, "a.amsj"); var bPath = Path.Combine(srcDir, "b.amsj");
                DocumentService.Save(aPath, new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "b.amsj" }) });
                DocumentService.Save(bPath, new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "a.amsj" }) });
                try { PlanExporter.Export(Path.Combine(outDir, "cycle-root.txt"), new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "a.amsj" }) }, pexSettings, 1920, 1080, rootPath, "TESTPC"); Assert(false, "v0.9.66: include cycle must block"); }
                catch (PlanExporter.PlanBlockedException bx) { Assert(bx.Errors.Any(e => e.Contains("include cycle")), "v0.9.66: include cycle guard reports the chain"); }

                // Root(0) -> d1(1) -> ... -> d4(4) is legal; a d5 child exceeds the cap.
                for (int d = 5; d >= 1; d--)
                {
                    var nodes = d == 5
                        ? new[] { PexStep("mouseClick") }
                        : new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "d" + (d + 1) + ".amsj" }) };
                    DocumentService.Save(Path.Combine(srcDir, "d" + d + ".amsj"), nodes);
                }
                try { PlanExporter.Export(Path.Combine(outDir, "depth-root.txt"), new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "d1.amsj" }) }, pexSettings, 1920, 1080, rootPath, "TESTPC"); Assert(false, "v0.9.66: include depth 5 must block"); }
                catch (PlanExporter.PlanBlockedException bx) { Assert(bx.Errors.Any(e => e.Contains("depth cap 4")), "v0.9.66: recursive include depth cap is four"); }

                // Force publication failure on child.txt after plan.txt moved; every old file returns.
                var rollbackOut = Path.Combine(pexBundleTmp, "rollback-out"); Directory.CreateDirectory(rollbackOut);
                var rollbackChild = Path.Combine(srcDir, "rollback-child.amsj");
                DocumentService.Save(rollbackChild, new[] { PexStep("mouseClick") });
                File.WriteAllText(Path.Combine(rollbackOut, "plan.txt"), "OLD PLAN");
                File.WriteAllText(Path.Combine(rollbackOut, "plan_engine.py"), "OLD ENGINE");
                File.WriteAllText(Path.Combine(rollbackOut, "README-PLAN.md"), "OLD README");
                Directory.CreateDirectory(Path.Combine(rollbackOut, "rollback-child.txt"));
                try { PlanExporter.Export(Path.Combine(rollbackOut, "plan.txt"), new[] { PexStep("playScript", new Dictionary<string, object?> { ["path"] = "rollback-child.amsj" }) }, pexSettings, 1920, 1080, rootPath, "TESTPC"); Assert(false, "v0.9.66: forced multi-file publish failure must throw"); }
                catch (IOException) { Assert(true, "v0.9.66: forced child-plan publish failure surfaced"); }
                Assert(File.ReadAllText(Path.Combine(rollbackOut, "plan.txt")) == "OLD PLAN" &&
                       File.ReadAllText(Path.Combine(rollbackOut, "plan_engine.py")) == "OLD ENGINE" &&
                       File.ReadAllText(Path.Combine(rollbackOut, "README-PLAN.md")) == "OLD README",
                    "v0.9.66: multi-file rollback restores the complete old bundle");
                Assert(!Directory.GetFiles(rollbackOut).Any(f => f.EndsWith(".tmp") || f.EndsWith(".bak")),
                    "v0.9.66: rollback removes all transaction artifacts");
            }
            finally { if (Directory.Exists(pexBundleTmp)) Directory.Delete(pexBundleTmp, true); }

            // Validator must close the exact top container and reject a second ELSE.
            static bool PexValidatorRejects(string plan, string fragment)
            {
                try
                {
                    typeof(PlanExporter).GetMethod("ValidatePlan", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!
                        .Invoke(null, new object[] { plan });
                    return false;
                }
                catch (System.Reflection.TargetInvocationException ex)
                {
                    return ex.InnerException is PlanExporter.PlanBlockedException bx && bx.Errors.Any(e => e.Contains(fragment));
                }
            }
            Assert(PexValidatorRejects("PLAN|2\nLOOP|1\nIFSND|1,1,1\nENDLOOP\nENDIF\n", "cannot close IF"),
                "v0.9.66: typed stack rejects cross-nested ENDLOOP");
            Assert(PexValidatorRejects("PLAN|2\nIFSND|1,1,1\nELSE\nELSE\nENDIF\n", "duplicate ELSE"),
                "v0.9.66: typed stack rejects duplicate ELSE");
            Assert(PexValidatorRejects("PLAN|2\nRPKG|all,1,1\nPGROUP\nENDPKG\nENDPAR\n", "cannot close PGROUP"),
                "v0.9.66: typed stack rejects package/group cross nesting");

'''
s = s.replace(anchor, block + anchor, 1)
p.write_text(s, encoding="utf-8", newline="\n")
print("PLAN2 recursive-bundle tests applied")
