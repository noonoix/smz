        // ── Step 59: v0.9.65 — portable plan exporter (PLAN|1 gen-1 contract, firmware 0.9.64b) ──
        Console.WriteLine();
        Console.WriteLine("--- Step 59: v0.9.65 plan exporter (PLAN|1) ---");
        {
            static string PexNormEol(string s) => s.Replace("\r\n", "\n").TrimEnd() + "\n";
            static string? PexReadRepo(string rel)
            {
                var dir = new DirectoryInfo(AppContext.BaseDirectory);
                for (int i = 0; i < 10 && dir is not null; i++, dir = dir.Parent)
                {
                    var cand = Path.Combine(dir.FullName, rel);
                    if (File.Exists(cand)) return File.ReadAllText(cand);
                }
                return null;
            }
            static StepNode PexStep(string type, Dictionary<string, object?>? props = null,
                                    int delay = 0, int delayMax = 0, bool disabled = false)
                => new() { Type = type, Props = props ?? new Dictionary<string, object?>(),
                           Delay = delay, DelayMax = delayMax, IsDisabled = disabled };
            static List<string> PexOps(string text)
                => text.Split('\n').Where(l => l.Length > 0 && !l.StartsWith("#")).ToList();

            var pexSettings = new AppSettings();

            // header + settings-driven SCREEN/SPEED
            var pexEmpty = PlanExporter.Compile(new List<StepNode>(), pexSettings, 1920, 1080, "fixture.amsj", "TESTPC");
            Assert(pexEmpty.Text.StartsWith("PLAN|1\n") && pexEmpty.Text.Contains("\nSCREEN|1920,1080\n")
                   && pexEmpty.Text.Contains("\nSPEED|300,2000\n"),
                "v0.9.65: plan header is PLAN|1 with SCREEN and SPEED from settings");

            // randomMousePosition: the exact golden line (proven by sim_plan_export.py on the real engine)
            var pexRand = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("randomMousePosition", new Dictionary<string, object?>
                {
                    ["x"] = 1301, ["y"] = 0, ["w"] = 378, ["h"] = 1049,
                    ["pauseBeforeMin"] = 120, ["pauseBeforeMax"] = 450,
                    ["pauseAfterMin"] = 150, ["pauseAfterMax"] = 600,
                    ["midPauseChance"] = 12, ["midPauseMin"] = 100, ["midPauseMax"] = 500,
                    ["idleEveryMin"] = 5, ["idleEveryMax"] = 12, ["idlePauseMin"] = 800, ["idlePauseMax"] = 3000,
                    ["overshootChance"] = 25, ["curveMinPct"] = 22, ["curveMaxPct"] = 155,
                    ["moveTimeMin"] = 0, ["moveTimeMax"] = 333,
                }, delay: 55, delayMax: 55),
            }, pexSettings, 1920, 1080, "fixture.amsj", "TESTPC");
            Assert(pexRand.Text.Contains("RMOUSE|region=1301,0,378,1049|before=120,450|after=150,600|curve=22,155|mid=12:100,500|over=25|mt=0,333|idle=5,12:800,3000\n"),
                "v0.9.65: randomMousePosition emits the exact golden RMOUSE line");
            Assert(pexRand.Text.TrimEnd().EndsWith("DELAY|55,55"),
                "v0.9.65: per-step delay-after lands after the op");
            Assert(pexRand.Counts.Contains("RMOUSE x1") && pexRand.Disabled.Count == 0,
                "v0.9.65: emission counts are reported");

            // mouseMove -> deterministic 1x1 RMOUSE region; idle explicitly OFF (gen-1 defaults it ON)
            var pexMove = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("mouseMove", new Dictionary<string, object?> { ["x"] = 700, ["y"] = 400, ["human"] = true }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexMove.Text.Contains("RMOUSE|region=700,400,1,1|before=60,220|after=80,280|curve=20,40|mid=6:80,250|over=12|idle=1,1:0,0\n"),
                "v0.9.65: mouseMove compiles to the deterministic 1x1 region with idle explicitly off");
            Assert(!pexMove.Text.Contains("idle=5,12"),
                "v0.9.65: the engine's built-in idle default never leaks into a point move");
            var pexNoHuman = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("mouseMove", new Dictionary<string, object?> { ["x"] = 5, ["y"] = 6, ["human"] = false }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexNoHuman.Flags.Any(f => f.Contains("instant (non-human) move")),
                "v0.9.65: human=false is flagged, never silent");

            // CLICK with swapped hold bounds
            var pexClick = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("mouseClick", new Dictionary<string, object?>
                { ["button"] = "right", ["action"] = "double", ["holdMin"] = 90, ["holdMax"] = 30 }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexClick.Text.Contains("CLICK|btn=right|n=2|hold=30,90\n"),
                "v0.9.65: click line with swap-normalized hold");

            // TYPE %-encoding + word pauses + settings cadence defaults
            var pexType = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("typeText", new Dictionary<string, object?> { ["text"] = "Hello 50%|world\nline2", ["hmin"] = 90, ["hmax"] = 180 }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexType.Text.Contains("TYPE|text=Hello 50%25%7Cworld%0Aline2|h=90,180\n"),
                "v0.9.65: TYPE percent-encoding (% -> %25, | -> %7C, newline -> %0A)");
            var pexWords = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("typeText", new Dictionary<string, object?> { ["text"] = "hi there you", ["wmin"] = 100, ["wmax"] = 180, ["wordPauseChance"] = 100 }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexWords.Text.Contains("TYPE|text=hi there you|h=80,220|w=100,180|wp=100\n"),
                "v0.9.65: word pauses + typing cadence defaults from settings");

            // the 23-action x port matrix: 15 types are BLOCKED with a named reason, never silently skipped
            var pexBlockedNeedles = new Dictionary<string, string>
            {
                ["findImage"] = "machine vision",
                ["waitForSound"] = "no WSND op",
                ["keystroke"] = "no KEY op",
                ["keyDown"] = "no KDOWN op",
                ["keyUp"] = "no KUP op",
                ["mouseScroll"] = "no WHEEL op",
                ["label"] = "LABEL/GOTO",
                ["gotoLabel"] = "LABEL/GOTO",
                ["rawCommand"] = "gen-2",
                ["randomPackage"] = "RPKG",
                ["parallelGroup"] = "PGROUP",
                ["playAudio"] = "no op",
                ["playScript"] = "INCLUDE",
                ["runExe"] = "Win+R",
                ["openFile"] = "Win+R",
            };
            foreach (var kv in pexBlockedNeedles)
            {
                try
                {
                    PlanExporter.Compile(new List<StepNode> { PexStep(kv.Key) }, pexSettings, 1920, 1080, "f", "T");
                    Assert(false, "v0.9.65: " + kv.Key + " must be blocked on PLAN|1");
                }
                catch (PlanExporter.PlanBlockedException bx)
                {
                    Assert(bx.Errors.Any(e => e.Contains(kv.Key) && e.Contains(kv.Value)),
                        "v0.9.65: " + kv.Key + " blocked with a named reason");
                }
            }
            foreach (var okType in new[] { "randomMousePosition", "mouseMove", "mouseClick", "delay", "waitForLight", "comment" })
            {
                var res = PlanExporter.Compile(new List<StepNode> { PexStep(okType) }, pexSettings, 1920, 1080, "f", "T");
                Assert(res.Text.StartsWith("PLAN|1"), "v0.9.65: " + okType + " compiles on PLAN|1");
            }
            var pexLoopOk = PlanExporter.Compile(new List<StepNode>
                { PexStep("forLoop", new Dictionary<string, object?> { ["mode"] = "count", ["count"] = 1 }) },
                pexSettings, 1920, 1080, "f", "T");
            Assert(pexLoopOk.Text.Contains("\nLOOP|1\n"), "v0.9.65: forLoop compiles on PLAN|1");

            // typing blockers
            try
            {
                PlanExporter.Compile(new List<StepNode> { PexStep("typeText", new Dictionary<string, object?> { ["text"] = "\u0633\u0644\u0627\u0645" }) }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: non-ASCII typing must be blocked");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Any(e => e.Contains("non-ASCII")), "v0.9.65: non-ASCII typing blocked with the ASCII rule");
            }
            try
            {
                PlanExporter.Compile(new List<StepNode> { PexStep("typeText", new Dictionary<string, object?> { ["text"] = "x", ["secret"] = true }) }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: secret typing must be blocked");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Any(e => e.Contains("clipboard")), "v0.9.65: secret typing blocked (no PC clipboard on the Pico)");
            }
            try
            {
                PlanExporter.Compile(new List<StepNode> { PexStep("typeText", new Dictionary<string, object?> { ["text"] = "x", ["mode"] = "clipboard" }) }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: clipboard mode must be blocked");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Any(e => e.Contains("clipboard mode")), "v0.9.65: clipboard mode blocked");
            }

            // If/Else heads: blocked once, markers consumed without stray-marker cascade
            var pexIf = PexStep("waitForLight", new Dictionary<string, object?> { ["insertIfElse"] = true });
            pexIf.Children.Add(PexStep("delay", new Dictionary<string, object?> { ["minMs"] = 5, ["maxMs"] = 5 }));
            try
            {
                PlanExporter.Compile(new List<StepNode>
                {
                    pexIf,
                    PexStep("comment", new Dictionary<string, object?> { ["text"] = "Else" }),
                    PexStep("comment", new Dictionary<string, object?> { ["text"] = "End If" }),
                }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: insertIfElse must be blocked on PLAN|1");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Count == 1 && bx.Errors[0].Contains("If/Else needs the gen-2 plan engine"),
                    "v0.9.65: If/Else blocked once - Else/End If markers consumed without cascade");
            }
            // nested blockers inside a blocked findImage head are still NAMED
            var pexFi = PexStep("findImage", new Dictionary<string, object?> { ["insertIfElse"] = true });
            pexFi.Children.Add(PexStep("findImage"));
            pexFi.Children.Add(PexStep("typeText", new Dictionary<string, object?> { ["text"] = "x", ["secret"] = true }));
            try
            {
                PlanExporter.Compile(new List<StepNode>
                {
                    pexFi,
                    PexStep("comment", new Dictionary<string, object?> { ["text"] = "Else" }),
                    PexStep("comment", new Dictionary<string, object?> { ["text"] = "End If" }),
                }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: findImage must be blocked");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Count == 3,
                    "v0.9.65: nested findImage + secret typing are NAMED inside a blocked head (3 errors)");
            }
            // stray structural marker
            try
            {
                PlanExporter.Compile(new List<StepNode> { PexStep("comment", new Dictionary<string, object?> { ["text"] = "Next" }) }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: a stray Next marker must be an error");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Any(e => e.Contains("no matching block head")), "v0.9.65: stray marker error");
            }
            // unknown step type
            try
            {
                PlanExporter.Compile(new List<StepNode> { PexStep("mysteryNewStep") }, pexSettings, 1920, 1080, "f", "T");
                Assert(false, "v0.9.65: an unknown step type must be an error");
            }
            catch (PlanExporter.PlanBlockedException bx)
            {
                Assert(bx.Errors.Any(e => e.Contains("unknown step type")), "v0.9.65: unknown step type error");
            }

            // forLoop modes + the Next marker consumption
            var pexLoop = PexStep("forLoop", new Dictionary<string, object?> { ["mode"] = "count", ["count"] = 2 });
            pexLoop.Children.Add(PexStep("mouseClick", new Dictionary<string, object?> { ["button"] = "left", ["action"] = "single" }));
            var pexLoopPlan = PlanExporter.Compile(new List<StepNode>
            {
                pexLoop,
                PexStep("comment", new Dictionary<string, object?> { ["text"] = "Next" }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexLoopPlan.Text.Contains("\nLOOP|2\n") && pexLoopPlan.Text.Contains("\nENDLOOP\n"),
                "v0.9.65: forLoop emits LOOP|2 ... ENDLOOP");
            Assert(!PexOps(pexLoopPlan.Text).Any(l => l == "# Next") && pexLoopPlan.Text.Split('\n').Count(l => l == "# Next") == 0,
                "v0.9.65: the loop head consumes its Next marker");
            var pexLoopTime = PlanExporter.Compile(new List<StepNode>
                { PexStep("forLoop", new Dictionary<string, object?> { ["mode"] = "time", ["timeValue"] = 5, ["timeUnit"] = "minute" }) },
                pexSettings, 1920, 1080, "f", "T");
            Assert(pexLoopTime.Text.Contains("\nLOOPTIME|300\n"), "v0.9.65: forLoop time 5 minute -> LOOPTIME|300");
            var pexLoopInf = PlanExporter.Compile(new List<StepNode>
                { PexStep("forLoop", new Dictionary<string, object?> { ["mode"] = "infinite" }) },
                pexSettings, 1920, 1080, "f", "T");
            Assert(pexLoopInf.Text.Contains("\nLOOP|0\n"), "v0.9.65: infinite loop -> LOOP|0");

            // Play Options wrapper (hard rule): once = bare, times N = LOOP|N, timed = LOOPTIME|seconds
            var pexTimes = PlanExporter.Compile(new List<StepNode> { PexStep("mouseClick") },
                new AppSettings { PlayRepeatMode = "times", PlayRepeatTimes = 3 }, 1920, 1080, "f", "T");
            var pexTimesOps = PexOps(pexTimes.Text);
            Assert(pexTimesOps[3] == "LOOP|3" && pexTimesOps[^1] == "ENDLOOP",
                "v0.9.65: Play Options times-3 wraps the whole body");
            var pexTimed = PlanExporter.Compile(new List<StepNode> { PexStep("mouseClick") },
                new AppSettings { PlayRepeatMode = "timed", PlayRepeatValue = 1, PlayRepeatUnit = "minute" }, 1920, 1080, "f", "T");
            Assert(pexTimed.Text.Contains("\nLOOPTIME|60\n"), "v0.9.65: Play Options timed 1 minute -> LOOPTIME|60");

            // waitForLight plain + armed (fractional stableSec -> ms)
            var pexLight = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("waitForLight", new Dictionary<string, object?>
                { ["luxCenter"] = 1250, ["luxTolerance"] = 50, ["stableSec"] = 0.5, ["timeoutMs"] = 9000, ["sampleMode"] = "lowres" }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexLight.Text.Contains("WLIGHT|1200,1300,500,9000,1\n"),
                "v0.9.65: plain WLIGHT (fractional stableSec becomes ms)");
            var pexArmed = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("waitForLight", new Dictionary<string, object?>
                { ["luxCenter"] = 1000, ["luxTolerance"] = 100, ["stableSec"] = 2, ["timeoutMs"] = 20000, ["sampleMode"] = "hires",
                  ["armed"] = true, ["key"] = "F4", ["holdMin"] = 30, ["holdMax"] = 90, ["reactMin"] = 80, ["reactMax"] = 180 }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(pexArmed.Text.Contains("WLIGHT|900,1100,2000,20000,0|key=115,30,90|react=80,180\n"),
                "v0.9.65: armed WLIGHT with key + react");

            // disabled steps counted and skipped; comments become # lines
            var pexDis = PlanExporter.Compile(new List<StepNode>
            {
                PexStep("mouseClick", disabled: true),
                PexStep("comment", new Dictionary<string, object?> { ["text"] = "hello note" }),
            }, pexSettings, 1920, 1080, "f", "T");
            Assert(!pexDis.Text.Contains("CLICK|") && pexDis.Text.Contains("# hello note") && pexDis.Disabled.Count == 1,
                "v0.9.65: disabled steps are counted and skipped; comments become # lines");

            // KeyboardBoard=promicro is a documented FLAG (bridge-mode only)
            var pexArm = PlanExporter.Compile(new List<StepNode> { PexStep("typeText", new Dictionary<string, object?> { ["text"] = "abc" }) },
                new AppSettings { KeyboardBoard = "promicro" }, 1920, 1080, "f", "T");
            Assert(pexArm.Flags.Any(f => f.Contains("KeyboardBoard=promicro")) && pexArm.Text.Contains("# FLAG"),
                "v0.9.65: KeyboardBoard=promicro is a documented FLAG, not silent");

            // delay swap normalization + a container's delay-after lands AFTER its ENDLOOP
            var pexDelay = PlanExporter.Compile(new List<StepNode>
                { PexStep("delay", new Dictionary<string, object?> { ["minMs"] = 500, ["maxMs"] = 100 }) },
                pexSettings, 1920, 1080, "f", "T");
            Assert(pexDelay.Text.Contains("\nDELAY|100,500\n"), "v0.9.65: delay step is swap-normalized");
            var pexLoopD = PexStep("forLoop", new Dictionary<string, object?> { ["mode"] = "count", ["count"] = 1 }, delay: 250);
            pexLoopD.Children.Add(PexStep("delay", new Dictionary<string, object?> { ["minMs"] = 5, ["maxMs"] = 5 }));
            var pexLoopDOps = PexOps(PlanExporter.Compile(new List<StepNode> { pexLoopD }, pexSettings, 1920, 1080, "f", "T").Text);
            Assert(pexLoopDOps[^1] == "DELAY|250" && pexLoopDOps[^2] == "ENDLOOP",
                "v0.9.65: a container's delay-after lands AFTER its ENDLOOP (app semantics)");

            // the embedded engine is the on-drive gen-1 engine, byte for byte
            var pexEngineOnDisk = PexReadRepo(Path.Combine("firmware", "code64b", "plan_engine.py"));
            Assert(pexEngineOnDisk is not null,
                "v0.9.65: firmware/code64b/plan_engine.py found next to the repo for the golden compare");
            Assert(pexEngineOnDisk is not null && PexNormEol(pexEngineOnDisk!) == PexNormEol(PlanExporter.BuildEnginePy()),
                "v0.9.65: the embedded plan engine is byte-identical to firmware/code64b/plan_engine.py");
            Assert(PlanExporter.PlanFormatVersion == 1 && PlanExporter.EngineVersion == PicoFirmwareExporter.BundleVersion,
                "v0.9.65: the plan exporter targets the current firmware bundle line (PLAN|1)");

            // Export() writes the whole bundle
            var pexTmp = Path.Combine(Path.GetTempPath(), "pex59_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(pexTmp);
            try
            {
                var pexWritten = PlanExporter.Export(Path.Combine(pexTmp, "plan.txt"),
                    new List<StepNode> { PexStep("randomMousePosition", new Dictionary<string, object?> { ["x"] = 100, ["y"] = 100, ["w"] = 200, ["h"] = 200 }) },
                    pexSettings, 1920, 1080, "fixture.amsj", "TESTPC");
                Assert(pexWritten.Count == 3 && File.Exists(Path.Combine(pexTmp, "plan.txt"))
                       && File.Exists(Path.Combine(pexTmp, "plan_engine.py")) && File.Exists(Path.Combine(pexTmp, "README-PLAN.md")),
                    "v0.9.65: Export writes plan.txt + plan_engine.py + README-PLAN.md");
                Assert(File.ReadAllText(Path.Combine(pexTmp, "plan.txt")).StartsWith("PLAN|1\n")
                       && File.ReadAllText(Path.Combine(pexTmp, "plan_engine.py")).Contains("def parse_plan"),
                    "v0.9.65: the written bundle carries the plan and the real engine");
            }
            finally { if (Directory.Exists(pexTmp)) Directory.Delete(pexTmp, true); }
        }

