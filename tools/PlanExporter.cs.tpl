using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// v0.9.65 - File → Export Pico Plan… (phase 2 of the portable line): compiles the open step
/// tree into a portable plan.txt for the Pico. Generated from tools/PlanExporter.cs.tpl by
/// tools/make_plan_exporter.py (the gen-1 engine is spliced in from firmware/code64b/plan_engine.py -
/// never edit the embedded copy by hand). Sandbox-proven by sim/sim_plan_export.py against the
/// real engine (54/54). Narrowed to the GEN-1 contract.
///
/// Target contract (project page, 2026-09-10): the gen-1 plan engine on the drive (firmware
/// pico-light 0.9.64b = firmware/code64b/plan_engine.py) accepts ONLY the header PLAN|1 and its
/// 11 ops: PLAN, SCREEN, SPEED, RMOUSE, CLICK, TYPE, DELAY, LOOP, LOOPTIME, ENDLOOP, WLIGHT.
/// The gen-3 engine (PLAN|2, portable/plan3/tools/plan_gen.py) belongs to the parked 0.9.66
/// line, so every step that needs it is a BLOCKING ERROR here - never silently skipped.
///
/// Compiled (8 of the 23 app actions): randomMousePosition, mouseMove (emitted as a
/// deterministic 1x1 RMOUSE region - the engine draws tx=randint(x, x+0)=x every pass),
/// mouseClick, typeText, delay, forLoop, waitForLight (plain + armed), comment. Blocked (15):
/// findImage, waitForSound, keystroke, keyDown, keyUp, mouseScroll, label, gotoLabel,
/// rawCommand, randomPackage, parallelGroup, playAudio, playScript, runExe, openFile.
/// If/Else heads (insertIfElse) are blocked too - IFLUX/ELSE/ENDIF are gen-2 ops.
///
/// Gen-1 compensations vs plan_gen (gen-3): the gen-1 engine DEFAULTS mid-pauses ON (12%) and
/// idle breaks ON (1000-5000 ms every 5-12 moves) when a key is omitted, so this exporter emits
/// mid= and idle= EXPLICITLY on every move (mid=0:0,0 / idle=1,1:0,0 disable them), and the
/// mouseMove emulation always carries idle=1,1:0,0 (a point-to-point move never idles).
/// </summary>
public static class PlanExporter
{
    /// <summary>The on-drive engine format this exporter targets (firmware pico-light 0.9.64b).</summary>
    public const int PlanFormatVersion = 1;
    public const string EngineVersion = "0.9.64b";

    /// <summary>One successful compilation: the plan text plus the human-readable reports.</summary>
    public sealed record PlanResult(string Text, IReadOnlyList<string> Flags,
                                    IReadOnlyList<string> Disabled, IReadOnlyList<string> Counts);

    /// <summary>Thrown when any step cannot be expressed on PLAN|1 - the file is NOT written.</summary>
    public sealed class PlanBlockedException : Exception
    {
        public IReadOnlyList<string> Errors { get; }
        public PlanBlockedException(IReadOnlyList<string> errors)
            : base("plan export blocked: " + errors.Count + " problem(s)") => Errors = errors;
    }

    private static readonly Dictionary<string, int> TimeUnitSec = new()
    { ["second"] = 1, ["minute"] = 60, ["hour"] = 3600 };

    private static readonly HashSet<string> Conditional = new() { "findImage", "waitForSound", "waitForLight" };
    private static readonly HashSet<string> LoopOwners = new() { "forLoop", "randomPackage", "parallelGroup" };

    // Bare-modifier aliases on top of KeyMap.VK (plan_gen parity: the armed-key field accepts them).
    private static readonly Dictionary<string, int> VkAliases = new()
    { ["SHIFT"] = 160, ["CTRL"] = 162, ["CONTROL"] = 162, ["ALT"] = 164, ["WIN"] = 91, ["LWIN"] = 91 };

    private static (int, int) Pair(int mn, int mx) => mx < mn ? (mx, mn) : (mn, mx);

    /// <summary>TYPE text encoder: '|', '%' and newline are structural in plan.txt; the board
    /// types ASCII 0x20-0x7E only, anything else is a blocking error (2026-09-04 decision).</summary>
    private static string PctType(string text)
    {
        var sb = new StringBuilder();
        foreach (var ch in text.Replace("\r\n", "\n").Replace("\r", "\n"))
        {
            if (ch == '\n') sb.Append("%0A");
            else if (ch == '%') sb.Append("%25");
            else if (ch == '|') sb.Append("%7C");
            else if (ch >= 32 && ch <= 126) sb.Append(ch);
            else throw new FormatException(
                "non-ASCII/control character '" + ch + "' - the board types ASCII only. "
                + "Keep the text Latin (non-Latin typing is out of scope for the port).");
        }
        return sb.ToString();
    }

    /// <summary>The app's structural markers are comment steps: Next / Else… / End If.</summary>
    private static bool IsMarker(StepNode n, string? kind = null)
    {
        if (n.Type != "comment") return false;
        var t = PropEx.GetString(n.Props, "text").Trim().ToLowerInvariant();
        return kind switch
        {
            "next" => t == "next",
            "else" => t.StartsWith("else", StringComparison.Ordinal),
            "endif" => t.StartsWith("end if", StringComparison.Ordinal),
            _ => t == "next" || t.StartsWith("else", StringComparison.Ordinal)
                 || t.StartsWith("end if", StringComparison.Ordinal),
        };
    }

    private sealed class Gen
    {
        private readonly AppSettings _settings;
        public readonly List<string> Lines = new();
        public readonly List<string> Errors = new();
        public readonly List<string> Flags = new();
        public readonly List<string> Disabled = new();
        public readonly Dictionary<string, int> Counts = new();
        public int Markers;
        private readonly Dictionary<StepNode, string> _numbering = new();

        public Gen(AppSettings settings) => _settings = settings;

        public void NumberTree(IEnumerable<StepNode> nodes, string prefix)
        {
            int i = 0;
            foreach (var n in nodes)
            {
                i++;
                var num = prefix.Length > 0 ? prefix + "." + i : i.ToString(CultureInfo.InvariantCulture);
                _numbering[n] = num;
                NumberTree(n.Children, num);
            }
        }

        private string Num(StepNode n) => _numbering.TryGetValue(n, out var s) ? s : "?";

        private string Title(StepNode n)
        {
            var name = (n.Name ?? "").Trim();
            return "step " + Num(n) + " (" + n.Type + ")" + (name.Length > 0 ? " - «" + name + "»" : "");
        }

        public void Error(StepNode n, string msg) => Errors.Add(Title(n) + ": " + msg);

        public void Flag(StepNode n, string msg)
        {
            Flags.Add(Title(n) + ": " + msg);
            Lines.Add("# FLAG " + Flags[^1]);
        }

        private void Count(string key) => Counts[key] = Counts.TryGetValue(key, out var c) ? c + 1 : 1;

        private void Emit(StepNode n, IEnumerable<string> ops, string? countType = null)
        {
            Lines.AddRange(ops);
            Count(countType ?? n.Type);
            EmitDelay(n);
        }

        /// <summary>Per-step 'delay after' - exactly the app's Delay / DelayMax semantics.</summary>
        private void EmitDelay(StepNode n)
        {
            int d = n.Delay, dm = n.DelayMax;
            if (dm > 0)
            {
                var (lo, hi) = Pair(d, dm);
                if (hi > 0) Lines.Add("DELAY|" + lo.ToString(CultureInfo.InvariantCulture) + "," + hi.ToString(CultureInfo.InvariantCulture));
            }
            else if (d > 0)
            {
                Lines.Add("DELAY|" + d.ToString(CultureInfo.InvariantCulture));
            }
        }

        public void Walk(IList<StepNode> nodes)
        {
            int i = 0;
            while (i < nodes.Count)
            {
                var n = nodes[i];
                if (n.IsDisabled)
                {
                    Disabled.Add(Title(n));
                    i++;
                    continue;
                }
                if (IsMarker(n))
                {
                    Error(n, "structural marker '" + PropEx.GetString(n.Props, "text").Trim() + "' has no matching "
                             + "block head - open and re-save the plan in the app (it self-heals), then export again");
                    i++;
                    continue;
                }
                if (Conditional.Contains(n.Type) && PropEx.GetBool(n.Props, "insertIfElse"))
                {
                    i = EmitIf(nodes, i);
                    continue;
                }
                EmitStep(n);
                i = LoopOwners.Contains(n.Type) ? ConsumeNext(nodes, i) : i + 1;
            }
        }

        /// <summary>A loop/package/group head owns the following Next marker (v0.9.48).</summary>
        private int ConsumeNext(IList<StepNode> nodes, int i)
        {
            if (i + 1 < nodes.Count && IsMarker(nodes[i + 1], "next"))
            {
                Markers++;
                return i + 2;
            }
            return i + 1;
        }

        /// <summary>An insertIfElse head is a BLOCKING error on PLAN|1 (IFLUX/ELSE/ENDIF are gen-2);
        /// its Else/End If markers are still consumed so they do not cascade as stray-marker errors,
        /// and nested blockers are still NAMED.</summary>
        private int EmitIf(IList<StepNode> nodes, int i)
        {
            var n = nodes[i];
            StepNode? elseNode = null, endifNode = null;
            int j = i + 1;
            if (j < nodes.Count && IsMarker(nodes[j], "else")) { elseNode = nodes[j]; j++; }
            if (j < nodes.Count && IsMarker(nodes[j], "endif")) { endifNode = nodes[j]; j++; }
            if (n.Type == "findImage")
            {
                Error(n, "findImage needs machine vision - it cannot run on the Pico. Convert "
                         + "this step to Wait For Light (BH1750) or Wait For Sound in the app first");
                CollectBlockers(n);
            }
            else if (n.Type == "waitForSound")
            {
                Error(n, "waitForSound has no WSND op in the PLAN|1 contract of firmware "
                         + EngineVersion + " (the sound sensor needs the gen-2 line) - convert the "
                         + "trigger to Wait For Light, or keep this plan in PC mode");
            }
            else
            {
                Error(n, "If/Else needs the gen-2 plan engine (IFLUX/ELSE/ENDIF are not in the PLAN|1 "
                         + "contract of firmware " + EngineVersion + ") - uncheck 'Insert If-Else' so the "
                         + "step runs as a plain wait, or keep this plan in PC mode");
            }
            foreach (var sub in new[] { elseNode, endifNode })
                if (sub is not null) { Markers++; CollectBlockers(sub); }
            return j;
        }

        /// <summary>A blocked container hides its subtree from the walk; sweep it so every nested
        /// findImage/secret/clipboard step is still NAMED in the blocking report.</summary>
        private void CollectBlockers(StepNode node)
        {
            foreach (var c in node.Children)
            {
                if (c.IsDisabled) continue;
                if (c.Type == "findImage")
                    Error(c, "findImage needs machine vision - it cannot run on the Pico (nested "
                             + "inside an already-blocked step)");
                else if (c.Type == "typeText"
                         && (PropEx.GetBool(c.Props, "secret")
                             || PropEx.GetString(c.Props, "mode", "keystrokes") == "clipboard"))
                    Error(c, "secret/clipboard typing needs a PC clipboard (nested inside an "
                             + "already-blocked step)");
                CollectBlockers(c);
            }
        }

        private void EmitStep(StepNode n)
        {
            switch (n.Type)
            {
                case "comment": EmitComment(n); return;
                case "delay": EmitDelayStep(n); return;
                case "randomMousePosition": EmitRandomMouse(n); return;
                case "mouseMove": EmitMouseMove(n); return;
                case "mouseClick": EmitMouseClick(n); return;
                case "typeText": EmitTypeText(n); return;
                case "forLoop": EmitForLoop(n); return;
                case "waitForLight": EmitWaitForLight(n); return;

                case "findImage":
                    Error(n, "findImage needs machine vision - it cannot run on the Pico. Convert "
                             + "this step to Wait For Light (BH1750) or Wait For Sound in the app first");
                    CollectBlockers(n);
                    return;
                case "waitForSound":
                    Error(n, "waitForSound has no WSND op in the PLAN|1 contract of firmware "
                             + EngineVersion + " (the sound sensor needs the gen-2 line) - convert the "
                             + "trigger to Wait For Light, or keep this plan in PC mode");
                    return;
                case "keystroke":
                    Error(n, "the PLAN|1 engine of firmware " + EngineVersion + " has no KEY op (it types "
                             + "TEXT only) - a Keystroke cannot be expressed; use Type Text for ASCII text "
                             + "or keep this plan in PC mode until the gen-2 line ships");
                    return;
                case "keyDown":
                    Error(n, "the PLAN|1 engine of firmware " + EngineVersion + " has no KDOWN op - "
                             + "keep this plan in PC mode until the gen-2 line ships");
                    return;
                case "keyUp":
                    Error(n, "the PLAN|1 engine of firmware " + EngineVersion + " has no KUP op - "
                             + "keep this plan in PC mode until the gen-2 line ships");
                    return;
                case "mouseScroll":
                    Error(n, "the PLAN|1 engine of firmware " + EngineVersion + " has no WHEEL op - "
                             + "keep this plan in PC mode until the gen-2 line ships");
                    return;
                case "label":
                case "gotoLabel":
                    Error(n, "labels need the gen-2 engine (LABEL/GOTO are not in PLAN|1) - keep this "
                             + "plan in PC mode until the gen-2 line ships");
                    return;
                case "rawCommand":
                    Error(n, "RAW passthrough is a gen-2 op - on PLAN|1 the engine would reject the "
                             + "line; keep this plan in PC mode");
                    return;
                case "randomPackage":
                    Error(n, "random packages need the gen-2 engine (RPKG is not in PLAN|1) - keep this "
                             + "plan in PC mode until the gen-2 line ships");
                    return;
                case "parallelGroup":
                    Error(n, "parallel groups need the gen-2 engine (PGROUP is not in PLAN|1) - keep "
                             + "this plan in PC mode until the gen-2 line ships");
                    return;
                case "playAudio":
                    Error(n, "playAudio has no op in the PLAN|1 contract (the buzzer/BEEP belongs to "
                             + "the gen-2 line) - keep this plan in PC mode");
                    return;
                case "playScript":
                    Error(n, "playScript needs the gen-2 engine (INCLUDE is not in PLAN|1) - inline the "
                             + "child steps, or keep this plan in PC mode");
                    return;
                case "runExe":
                    Error(n, "runExe compiles to a Win+R macro on the gen-2 line only - PLAN|1 has no "
                             + "launch ops; keep this plan in PC mode");
                    return;
                case "openFile":
                    Error(n, "openFile compiles to a Win+R macro on the gen-2 line only - PLAN|1 has "
                             + "no launch ops; keep this plan in PC mode");
                    return;
                default:
                    Error(n, "unknown step type '" + n.Type + "' - this exporter does not know it "
                             + "(supported: the 23 app actions)");
                    return;
            }
        }

        private void EmitComment(StepNode n)
        {
            Lines.Add("# " + PropEx.GetString(n.Props, "text").Replace("\n", " "));
            Count("comment");
        }

        private void EmitDelayStep(StepNode n)
        {
            var (lo, hi) = Pair(PropEx.GetInt(n.Props, "minMs", 0), PropEx.GetInt(n.Props, "maxMs", 333));
            Emit(n, new[] { hi > lo ? "DELAY|" + lo + "," + hi : "DELAY|" + lo }, "DELAY");
        }

        /// <summary>The humanized-move layers; gen-1 forces EVERY key explicit (its built-in defaults
        /// enable mid-pauses at 12% and idle breaks at 1000-5000 ms - the app defaults differ, so an
        /// omitted key would change behavior on the Pico).</summary>
        private string Tuning(StepNode n, (int i0, int i1, int p0, int p1) idle)
        {
            var p = n.Props;
            var (b0, b1) = Pair(PropEx.GetInt(p, "pauseBeforeMin", 60), PropEx.GetInt(p, "pauseBeforeMax", 220));
            var (a0, a1) = Pair(PropEx.GetInt(p, "pauseAfterMin", 80), PropEx.GetInt(p, "pauseAfterMax", 280));
            var (c0, c1) = Pair(PropEx.GetInt(p, "curveMinPct", 20), PropEx.GetInt(p, "curveMaxPct", 40));
            var parts = new List<string>
            {
                "before=" + b0 + "," + b1,
                "after=" + a0 + "," + a1,
                "curve=" + c0 + "," + c1,
            };
            var mch = Math.Max(0, Math.Min(100, PropEx.GetInt(p, "midPauseChance", 6)));
            var (m0, m1) = Pair(PropEx.GetInt(p, "midPauseMin", 80), PropEx.GetInt(p, "midPauseMax", 250));
            parts.Add("mid=" + mch + ":" + m0 + "," + m1);
            parts.Add("over=" + Math.Max(0, Math.Min(100, PropEx.GetInt(p, "overshootChance", 12))));
            var (t0, t1) = Pair(PropEx.GetInt(p, "moveTimeMin", 0), PropEx.GetInt(p, "moveTimeMax", 0));
            if (t1 > 0) parts.Add("mt=" + t0 + "," + t1);
            parts.Add("idle=" + idle.i0 + "," + idle.i1 + ":" + idle.p0 + "," + idle.p1);
            return "|" + string.Join("|", parts);
        }

        private void EmitRandomMouse(StepNode n)
        {
            var p = n.Props;
            int x = PropEx.GetInt(p, "x", 1301), y = PropEx.GetInt(p, "y", 0);
            int w = PropEx.GetInt(p, "w", 378), h = PropEx.GetInt(p, "h", 1049);
            if (w <= 0 || h <= 0)
            {
                Error(n, "region width/height must be positive (got " + w + "x" + h + ")");
                return;
            }
            var (i0, i1) = Pair(PropEx.GetInt(p, "idleEveryMin", 5), PropEx.GetInt(p, "idleEveryMax", 12));
            var (p0, p1) = Pair(PropEx.GetInt(p, "idlePauseMin", 800), PropEx.GetInt(p, "idlePauseMax", 3000));
            var idle = p1 > 0 ? (i0, i1, p0, p1) : (1, 1, 0, 0);   // explicit-off, not the engine default
            Emit(n, new[] { "RMOUSE|region=" + x + "," + y + "," + w + "," + h + Tuning(n, idle) }, "RMOUSE");
        }

        private void EmitMouseMove(StepNode n)
        {
            int x = PropEx.GetInt(n.Props, "x", 600), y = PropEx.GetInt(n.Props, "y", 497);
            if (!PropEx.GetBool(n.Props, "human", true))
                Flag(n, "instant (non-human) move is not in the PLAN|1 contract - a humanized move to "
                        + "the exact point was emitted instead");
            Emit(n, new[] { "RMOUSE|region=" + x + "," + y + ",1,1" + Tuning(n, (1, 1, 0, 0)) }, "MOVETO");
        }

        private void EmitMouseClick(StepNode n)
        {
            var p = n.Props;
            var btn = PropEx.GetString(p, "button", "left");
            if (btn is not ("left" or "middle" or "right"))
            {
                Error(n, "unknown mouse button '" + btn + "'");
                return;
            }
            int count = PropEx.GetString(p, "action", "single") == "double" ? 2 : 1;
            var (hmin, hmax) = Pair(PropEx.GetInt(p, "holdMin", 0), PropEx.GetInt(p, "holdMax", 0));
            var line = "CLICK|btn=" + btn + "|n=" + count;
            if (hmax > 0) line += "|hold=" + hmin + "," + hmax;
            Emit(n, new[] { line }, "CLICK");
        }

        private void EmitTypeText(StepNode n)
        {
            var p = n.Props;
            if (PropEx.GetBool(p, "secret"))
            {
                Error(n, "secret steps type through the Windows clipboard, which does not exist on a "
                         + "bare Pico - re-enter the text as plain keystrokes (or keep this plan in PC mode)");
                return;
            }
            if (PropEx.GetString(p, "mode", "keystrokes") == "clipboard")
            {
                Error(n, "clipboard mode needs a PC clipboard - the portable plan can only type "
                         + "keystrokes. Switch the step to keystrokes mode (text must be ASCII)");
                return;
            }
            string text;
            try { text = PctType(PropEx.GetString(p, "text")); }
            catch (FormatException ex) { Error(n, ex.Message); return; }
            if (text.Length == 0) { Error(n, "empty text - nothing to type"); return; }

            var (hmin, hmax) = Pair(PropEx.GetInt(p, "hmin", _settings.TypeKeyMinMs),
                                    PropEx.GetInt(p, "hmax", _settings.TypeKeyMaxMs));
            var parts = new List<string> { "h=" + hmin + "," + hmax };
            var (wmin, wmax) = Pair(PropEx.GetInt(p, "wmin", 0), PropEx.GetInt(p, "wmax", 0));
            if (wmax > 0)
            {
                parts.Add("w=" + wmin + "," + wmax);
                if (p.ContainsKey("wordPauseChance"))
                    parts.Add("wp=" + Math.Max(0, Math.Min(100, PropEx.GetInt(p, "wordPauseChance", 100))));
            }
            var (pmin, pmax) = Pair(PropEx.GetInt(p, "pmin", 0), PropEx.GetInt(p, "pmax", 0));
            if (pmax > 0) parts.Add("p=" + pmin + "," + pmax);
            var tch = Math.Max(0, Math.Min(100, PropEx.GetInt(p, "thinkChance", 0)));
            if (tch > 0)
            {
                var (t0, t1) = Pair(PropEx.GetInt(p, "thinkMin", 800), PropEx.GetInt(p, "thinkMax", 2200));
                if (t1 > 0) parts.Add("think=" + tch + ":" + t0 + "," + t1);
            }
            var (y0, y1) = Pair(PropEx.GetInt(p, "typoEveryMin", 0), PropEx.GetInt(p, "typoEveryMax", 0));
            if (y1 > 0) parts.Add("typo=" + y0 + "," + y1);
            else if (PropEx.GetInt(p, "typoChance", 0) > 0)
                Flag(n, "legacy typoChance % is not portable - use 'typo every N words' (typoEveryMin/Max); "
                        + "the step types WITHOUT typos in this plan");
            Emit(n, new[] { "TYPE|text=" + text + "|" + string.Join("|", parts) }, "TYPE");
        }

        private void EmitForLoop(StepNode n)
        {
            var p = n.Props;
            var mode = PropEx.GetString(p, "mode", "count");
            string head;
            if (mode == "time")
            {
                var unit = PropEx.GetString(p, "timeUnit", "minute");
                if (!TimeUnitSec.TryGetValue(unit, out var factor))
                {
                    Error(n, "unknown time unit '" + unit + "'");
                    return;
                }
                var sec = PropEx.GetInt(p, "timeValue", 10) * factor;
                if (sec <= 0)
                {
                    Error(n, "loop time must be positive (got " + PropEx.GetInt(p, "timeValue", 10) + " " + unit + ")");
                    return;
                }
                head = "LOOPTIME|" + sec;
            }
            else if (mode == "infinite")
            {
                head = "LOOP|0";
            }
            else if (mode == "count")
            {
                var cnt = PropEx.GetInt(p, "count", 10);
                if (cnt <= 0)
                {
                    Error(n, "loop count must be positive (got " + cnt + ") - use 'infinite' for forever");
                    return;
                }
                head = "LOOP|" + cnt;
            }
            else
            {
                Error(n, "unknown loop mode '" + mode + "'");
                return;
            }
            Lines.Add(head);
            Count("LOOP");
            Walk(n.Children);
            Lines.Add("ENDLOOP");
            EmitDelay(n);   // the app's delay lands after the whole loop
        }

        private void EmitWaitForLight(StepNode n)
        {
            var p = n.Props;
            int center = PropEx.GetInt(p, "luxCenter", 1250);
            int tol = Math.Max(1, PropEx.GetInt(p, "luxTolerance", 50));
            int stable = Math.Max(0, (int)Math.Round(PropEx.GetDouble(p, "stableSec", 2) * 1000));
            int to = PropEx.GetInt(p, "timeoutMs", 20000);
            int mode = PropEx.GetString(p, "sampleMode", "hires") == "lowres" ? 1 : 0;
            int lo = Math.Max(0, center - tol), hi = center + tol;
            var head = "WLIGHT|" + lo + "," + hi + "," + stable + "," + to + "," + mode;
            if (PropEx.GetBool(p, "armed"))
            {
                var keyName = PropEx.GetString(p, "key", "E");
                if (!KeyMap.VK.TryGetValue(keyName, out var vk) && !VkAliases.TryGetValue(keyName, out vk))
                {
                    Error(n, "unknown key name '" + keyName + "' for waitForLight armed key");
                    return;
                }
                var (hmin, hmax) = Pair(PropEx.GetInt(p, "holdMin", 30), PropEx.GetInt(p, "holdMax", 90));
                var (rmin, rmax) = Pair(PropEx.GetInt(p, "reactMin", 80), PropEx.GetInt(p, "reactMax", 180));
                head += "|key=" + vk + "," + hmin + "," + hmax + "|react=" + rmin + "," + rmax;
            }
            Emit(n, new[] { head }, "WLIGHT");
        }
    }

    /// <summary>Compiles the step tree into plan text. Throws PlanBlockedException when any step
    /// cannot run on PLAN|1 - nothing is written in that case (never a partial plan).</summary>
    public static PlanResult Compile(IList<StepNode> roots, AppSettings settings,
        int screenW, int screenH, string sourceName, string machine)
    {
        var gen = new Gen(settings);
        gen.NumberTree(roots, "");
        gen.Walk(roots);

        var body = new List<string>(gen.Lines);
        // Play Options wrapper (hard rule): once = bare, times N = LOOP|N, timed = LOOPTIME|seconds
        var mode = settings.PlayRepeatMode;
        if (mode == "times")
        {
            if (settings.PlayRepeatTimes <= 0)
                gen.Errors.Add("settings: PlayRepeatTimes must be a positive integer (got " + settings.PlayRepeatTimes + ")");
            else
            {
                body.Insert(0, "LOOP|" + settings.PlayRepeatTimes);
                body.Add("ENDLOOP");
            }
        }
        else if (mode == "timed")
        {
            var unit = settings.PlayRepeatUnit;
            var sec = settings.PlayRepeatValue * (TimeUnitSec.TryGetValue(unit, out var f) ? f : 0);
            if (!TimeUnitSec.ContainsKey(unit) || sec <= 0)
                gen.Errors.Add("settings: bad timed repeat (" + settings.PlayRepeatValue + " " + unit + ")");
            else
            {
                body.Insert(0, "LOOPTIME|" + sec);
                body.Add("ENDLOOP");
            }
        }
        else if (mode != "once")
        {
            gen.Errors.Add("settings: unknown PlayRepeatMode '" + mode + "' (once|times|timed)");
        }
        if (settings.KeyboardBoard == "promicro")
        {
            gen.Flags.Add("settings: KeyboardBoard=promicro is bridge-mode only; on the portable plan "
                          + "the Pico types every keyboard step (keyboard=Pico contract)");
            body.Insert(0, "# FLAG " + gen.Flags[^1]);
        }
        if (gen.Errors.Count > 0) throw new PlanBlockedException(gen.Errors);

        var sb = new StringBuilder();
        sb.Append("PLAN|1\n");
        sb.Append("# generated by Classroom Studio PlanExporter (engine " + EngineVersion + ") from " + sourceName + "\n");
        sb.Append("# machine: " + machine + " · generated: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + "\n");
        sb.Append("SCREEN|" + screenW + "," + screenH + "\n");
        sb.Append("SPEED|" + settings.MouseMoveSpeedMin + "," + settings.MouseMoveSpeedMax + "\n\n");
        foreach (var l in body) sb.Append(l).Append('\n');
        var text = sb.ToString();
        ValidatePlan(text);   // dogfood: a generator bug must never reach a drive
        return new PlanResult(text, gen.Flags, gen.Disabled,
                              gen.Counts.OrderBy(kv => kv.Key).Select(kv => kv.Key + " x" + kv.Value).ToList());
    }

    /// <summary>Writes plan.txt (the compiled plan), plan_engine.py (the gen-1 engine) and
    /// README-PLAN.md next to <paramref name="planPath"/>. Returns the written paths.</summary>
    public static IReadOnlyList<string> Export(string planPath, IList<StepNode> steps,
        AppSettings settings, int screenW, int screenH, string sourceName, string machine)
    {
        var result = Compile(steps, settings, screenW, screenH, sourceName, machine);
        var full = Path.GetFullPath(planPath);
        var dir = Path.GetDirectoryName(full);
        if (string.IsNullOrEmpty(dir)) throw new IOException("cannot resolve the folder of " + planPath);
        var written = new List<string> { full };
        File.WriteAllText(full, result.Text);
        var enginePath = Path.Combine(dir, "plan_engine.py");
        File.WriteAllText(enginePath, BuildEnginePy());
        written.Add(enginePath);
        var readmePath = Path.Combine(dir, "README-PLAN.md");
        File.WriteAllText(readmePath, BuildReadme(result, sourceName, machine));
        written.Add(readmePath);
        return written;
    }

    /// <summary>The gen-1 plan engine, embedded verbatim (firmware/code64b/plan_engine.py).
    /// Normalized to LF so the written file is byte-stable regardless of the .cs line endings.</summary>
    public static string BuildEnginePy() => EngineTemplate.Replace("\r\n", "\n");

    private static string BuildReadme(PlanResult result, string sourceName, string machine)
    {
        var sb = new StringBuilder();
        sb.Append("# راهنمای پلن پرتابل پیکو (PLAN|1 - فریم‌ور 0.9.64b)\n\n");
        sb.Append("این سه فایل را روی درایو CIRCUITPY کپی کن (کنار code.py از «Export Pico Firmware»):\n");
        sb.Append("- plan.txt ← پلن کامپایل‌شده (همین فایل)\n");
        sb.Append("- plan_engine.py ← موتور gen-1 (فقط وقتی نسخه‌ی فریم‌ور عوض شود دوباره لازم است)\n\n");
        sb.Append("- منبع: " + sourceName + " · سیستم: " + machine + "\n");
        sb.Append("- استپ‌های کامپایل‌شده: " + (result.Counts.Count > 0 ? string.Join(" · ", result.Counts) : "-") + "\n");
        if (result.Disabled.Count > 0)
            sb.Append("- استپ‌های غیرفعال (شمرده شدند، اجرا نمی‌شوند): " + result.Disabled.Count + "\n");
        if (result.Flags.Count > 0)
        {
            sb.Append("\n## قیدها (FLAG)\n\n");
            foreach (var f in result.Flags) sb.Append("- " + f + "\n");
        }
        sb.Append("\n## اجرا روی برد\n\n");
        sb.Append("- Num Lock = شروع/توقف پلن · Scroll Lock = مکث/ادامه (همان کیپد روی برد)\n");
        sb.Append("- اگر کنسول «plan: load failed» + ۴ فلاش LED داد: نسخه‌ی هدر plan.txt با فریم‌ور نمی‌خواند ← دوباره اکسپورت کن.\n");
        sb.Append("- برای دیدن لاگ اجرا، PLAN_DEBUG را در code.py روشن کن و کنسول سریال را باز کن.\n");
        return sb.ToString();
    }

    /// <summary>Structural self-check mirroring the gen-1 parser: op whitelist, PLAN|1 first,
    /// loop balance, RMOUSE region quad, WLIGHT positionals, TYPE text=, DELAY/SCREEN/SPEED ints.
    /// A failure here is a generator BUG - it throws before anything reaches a file.</summary>
    private static void ValidatePlan(string text)
    {
        var stack = 0;
        var first = true;
        var lines = text.Split('\n');
        for (int li = 0; li < lines.Length; li++)
        {
            var line = lines[li].Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;
            var fields = line.Split('|');
            var op = fields[0];
            void Bad(string why) => throw new PlanBlockedException(new[] { "PlanExporter BUG: line " + (li + 1) + ": " + why + " (please report)" });
            switch (op)
            {
                case "PLAN":
                    if (!first || fields.Length < 2 || fields[1] != "1") Bad("PLAN must be first with version 1");
                    break;
                case "SCREEN":
                case "SPEED":
                    if (fields.Length < 2 || fields[1].Split(',').Length != 2
                        || !fields[1].Split(',').All(IsInt)) Bad(op + " needs exactly two ints");
                    break;
                case "DELAY":
                    if (fields.Length < 2 || !IsIntPair(fields[1])) Bad("DELAY needs one or two ints");
                    break;
                case "LOOP":
                case "LOOPTIME":
                    if (fields.Length < 2 || !long.TryParse(fields[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out _))
                        Bad(op + " needs a number");
                    stack++;
                    break;
                case "ENDLOOP":
                    if (stack <= 0) Bad("ENDLOOP without LOOP");
                    stack--;
                    break;
                case "RMOUSE":
                    if (!HasKv(fields, "region", out var rv) || rv.Split(',').Length != 4
                        || !rv.Split(',').All(IsInt)) Bad("RMOUSE needs region=x,y,w,h");
                    break;
                case "CLICK":
                    break;   // btn/n/hold all have engine-side defaults
                case "TYPE":
                    if (!HasKv(fields, "text", out _)) Bad("TYPE needs text=");
                    break;
                case "WLIGHT":
                    if (fields.Length < 2 || fields[1].Split(',').Length < 5
                        || !fields[1].Split(',').Take(5).All(IsInt)) Bad("WLIGHT needs lo,hi,stable,to,mode");
                    break;
                default:
                    Bad("unknown op '" + op + "'");
                    break;
            }
            first = false;
        }
        if (stack != 0)
            throw new PlanBlockedException(new[] { "PlanExporter BUG: LOOP without ENDLOOP (please report)" });
    }

    private static bool IsInt(string s)
        => int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out _);

    private static bool IsIntPair(string s)
    {
        var parts = s.Split(',');
        return parts.Length is >= 1 and <= 2 && parts.All(IsInt);
    }

    private static bool HasKv(string[] fields, string key, out string value)
    {
        foreach (var f in fields.Skip(1))
            if (f.StartsWith(key + "=", StringComparison.Ordinal)) { value = f[(key.Length + 1)..]; return true; }
        value = "";
        return false;
    }

    // The gen-1 plan engine (firmware/code64b/plan_engine.py) is spliced in here by
    // tools/make_plan_exporter.py as a 4-quote raw string (the engine holds docstrings).
    // TestRunner compares the embedded copy byte-for-byte against the repo golden
    // (modulo line endings), so the template can never drift from the firmware line it targets.
    private const string EngineTemplate = __ENGINE_TEMPLATE__;
}
