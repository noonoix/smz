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
            // explicit-off is read from the RAW idlePauseMax (max pause = 0 => no idle breaks),
            // BEFORE Pair swaps the bounds - otherwise (min=800, max=0) swaps to (0,800) and the
            // off-intent is lost.
            var idle = PropEx.GetInt(p, "idlePauseMax", 3000) > 0 ? (i0, i1, p0, p1) : (1, 1, 0, 0);
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
    private const string EngineTemplate = """"
# plan_engine.py - Classroom Studio portable plan engine (code64)
# Runs on the Pico (CircuitPython) and on CPython (the sim). Exact port of the app's
# humanization layers: WindMouse (HumanMouse.cs v0.9.24) and the typing planner
# (StepDefinitions.TypeScript v0.9.15). Fresh randomness is rolled for every pass,
# so repeated loops never replay an identical path - exactly like the PC app.
#
# plan.txt - one op per line, pipe-separated, key=value args, %-encoding inside text:
#   PLAN|1                                header (format version, must be first)
#   SCREEN|1920,1080                      clamp bounds for all moves
#   SPEED|0,2000                          app mouse speed px/s (max 0 = shape-only pacing)
#   RMOUSE|region=x,y,w,h|mt=mn,mx|curve=mn,mx|before=mn,mx|after=mn,mx|
#         mid=chance:mn,mx|idle=everyMn,everyMx:pauseMn,pauseMx|over=pct
#   CLICK|btn=left|n=1|hold=mn,mx
#   TYPE|h=mn,mx|w=mn,mx|wp=pct|p=mn,mx|think=chance:mn,mx|typo=mn,mx|text=<encoded>
#   DELAY|mn,mx
#   LOOP|n  ... ENDLOOP                   n = pass count, 0 = forever
#   LOOPTIME|sec ... ENDLOOP              repeats until the deadline passes
#   WLIGHT|lo,hi,stable_ms,timeout_ms,mode[|key=vk,hmn,hmx|react=mn,mx]
# Blank lines and lines starting with # are ignored. Unknown ops fail the whole file.

import time
import math
import random


class PlanAbort(Exception):
    """Raised inside a step when the host took over or the keypad stopped the run."""


# code64: optional persistent cursor contract. The Pico context owns the saved
# coordinate so Start/Stop does not reset every new run_plan() call to screen centre.
def _load_mouse_pos(ctx, ops):
    sw, sh = ctx.screen_w, ctx.screen_h
    for op, prm in ops:
        if op == "SCREEN":
            sw, sh = prm["v"]
            break
    saved = None
    getter = getattr(ctx, "get_mouse_pos", None)
    if getter is not None:
        try:
            saved = getter()
        except Exception:
            saved = None
    if saved is None or len(saved) < 2:
        return [sw // 2, sh // 2]
    return [_clamp(int(saved[0]), 0, max(0, sw - 1)),
            _clamp(int(saved[1]), 0, max(0, sh - 1))]


def _save_mouse_pos(ctx, pos):
    setter = getattr(ctx, "set_mouse_pos", None)
    if setter is not None:
        setter(int(pos[0]), int(pos[1]))


# ── rng helpers (mirror HumanMouse.Rand / RandRange: swap-tolerant, max<=0 → 0) ─────────

def _rf():
    return random.random()


def _below(n):            # C# Random.Next(n): 0..n-1
    return random.randrange(n) if n > 0 else 0


def rand_range(mn, mx):   # C# Rand: inclusive, swap-tolerant, 0 when max <= 0
    if mx < mn:
        mn, mx = mx, mn
    if mx <= 0:
        return 0
    return mn if mx <= mn else random.randint(mn, mx)


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# ── %-codec for TYPE text (|, %, newline are structural in plan.txt) ─────────────────────

def pct_dec(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s) + 1 and i + 2 <= len(s) - 1:
            try:
                out.append(chr(int(s[i + 1:i + 3], 16)))
                i += 3
                continue
            except Exception:
                pass
        out.append(s[i])
        i += 1
    return "".join(out)


# ── parser ───────────────────────────────────────────────────────────────────────────────

_OPS = ("PLAN", "SCREEN", "SPEED", "RMOUSE", "CLICK", "TYPE",
        "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "WLIGHT")


def _pair(s, what, line_no):
    parts = s.split(",")
    try:
        a, b = int(parts[0]), int(parts[1])
    except Exception:
        raise ValueError("line %d: bad %s '%s'" % (line_no, what, s))
    return (a, b) if b >= a else (b, a)     # normalize like the app (swap-tolerant)


def _quad(s, what, line_no):
    parts = s.split(",")
    if len(parts) != 4:
        raise ValueError("line %d: bad %s '%s'" % (line_no, what, s))
    try:
        return tuple(int(p) for p in parts)
    except Exception:
        raise ValueError("line %d: bad %s '%s'" % (line_no, what, s))


def parse_plan(text):
    """Returns [(op, params), ...]; params is a dict. Raises ValueError with line no."""
    ops = []
    loop_stack = []
    for line_no, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        op = fields[0].upper()
        if op not in _OPS:
            raise ValueError("line %d: unknown op '%s'" % (line_no, fields[0]))
        prm = {}
        if op in ("PLAN", "SCREEN", "SPEED", "DELAY", "LOOP", "LOOPTIME"):
            body = fields[1] if len(fields) > 1 else ""
            if op == "PLAN":
                try:
                    prm["v"] = int(body or "0")
                except Exception:
                    raise ValueError("line %d: bad PLAN version" % line_no)
                if prm["v"] != 1:
                    raise ValueError("line %d: unsupported PLAN version %d" % (line_no, prm["v"]))
            elif op == "SCREEN":
                parts = body.split(",")
                try:
                    # ordered pair: width,height are NOT a sortable range - _pair would
                    # swap 1920,1080 into 1080,1920 and clamp every x to the wrong axis
                    prm["v"] = (int(parts[0]), int(parts[1]))
                except Exception:
                    raise ValueError("line %d: bad SCREEN '%s'" % (line_no, body))
            elif op == "SPEED":
                prm["v"] = _pair(body, op, line_no)
            elif op == "DELAY":
                prm["v"] = _pair(body + ("," + body if "," not in body else ""), op, line_no)
            elif op == "LOOP":
                prm["n"] = int(body or "1")
                loop_stack.append((op, line_no))
            else:
                prm["sec"] = float(body or "0")
                loop_stack.append((op, line_no))
        elif op == "ENDLOOP":
            if not loop_stack:
                raise ValueError("line %d: ENDLOOP without LOOP" % line_no)
            loop_stack.pop()
        elif op == "WLIGHT":
            pos = fields[1].split(",") if len(fields) > 1 else []
            if len(pos) < 5:
                raise ValueError("line %d: WLIGHT needs lo,hi,stable,to,mode" % line_no)
            try:
                prm["lo"], prm["hi"] = int(pos[0]), int(pos[1])
                prm["stable"], prm["to"], prm["mode"] = int(pos[2]), int(pos[3]), int(pos[4])
            except Exception:
                raise ValueError("line %d: bad WLIGHT numbers" % line_no)
            for kv in fields[2:]:
                if "=" not in kv:
                    raise ValueError("line %d: bad arg '%s'" % (line_no, kv))
                k, v = kv.split("=", 1)
                if k == "key":
                    t = v.split(",")
                    prm["key"] = (int(t[0]), int(t[1]) if len(t) > 1 else 30,
                                  int(t[2]) if len(t) > 2 else 90)
                elif k == "react":
                    prm["react"] = _pair(v, k, line_no)
                else:
                    raise ValueError("line %d: unknown WLIGHT key '%s'" % (line_no, k))
        else:   # RMOUSE / CLICK / TYPE: key=value args
            for kv in fields[1:]:
                if "=" not in kv:
                    raise ValueError("line %d: bad arg '%s' (want key=value)" % (line_no, kv))
                k, v = kv.split("=", 1)
                prm[k] = v
            if op == "RMOUSE":
                if "region" not in prm:
                    raise ValueError("line %d: RMOUSE needs region=x,y,w,h" % line_no)
                prm["region"] = _quad(prm["region"], "region", line_no)
                for k in ("mt", "curve", "before", "after"):
                    if k in prm:
                        prm[k] = _pair(prm[k], k, line_no)
                if "mid" in prm:                       # chance:mn,mx
                    c, _, r = prm["mid"].partition(":")
                    prm["mid"] = (int(c), _pair(r, "mid", line_no))
                if "idle" in prm:                      # everyMn,everyMx:pauseMn,pauseMx
                    e, _, r = prm["idle"].partition(":")
                    prm["idle"] = (_pair(e, "idle-every", line_no), _pair(r, "idle-pause", line_no))
                if "over" in prm:
                    prm["over"] = int(prm["over"])
            elif op == "CLICK":
                prm["btn"] = prm.get("btn", "left")
                prm["n"] = int(prm.get("n", "1"))
                if "hold" in prm:
                    prm["hold"] = _pair(prm["hold"], "hold", line_no)
            elif op == "TYPE":
                if "text" not in prm:
                    raise ValueError("line %d: TYPE needs text=" % line_no)
                prm["text"] = pct_dec(prm["text"])
                for k in ("h", "w", "p", "typo"):
                    if k in prm:
                        prm[k] = _pair(prm[k], k, line_no)
                if "think" in prm:
                    c, _, r = prm["think"].partition(":")
                    prm["think"] = (int(c), _pair(r, "think", line_no))
                if "wp" in prm:
                    prm["wp"] = int(prm["wp"])
        ops.append((op, prm))
    if loop_stack:
        raise ValueError("line %d: LOOP without ENDLOOP" % loop_stack[-1][1])
    if not ops or ops[0][0] != "PLAN":
        raise ValueError("plan must start with PLAN|1")
    return ops


# ── HumanMouse port (C# v0.9.24 → Python; banker-rounding matches Math.Round) ───────────

def tuned_wind(dist, curve):
    cv = 0.30 if curve < 0 else _clamp(curve, 0.0, 2.0)
    base = 0.3 + cv * 3.0 if cv < 1.0 else 3.3 + (cv - 1.0) * 4.7
    return base * _clamp(dist / 400.0, 0.35, 1.0)


def build_range_profile(mn, mx, knot_count, low_ends=False):
    if mx < mn:
        mn, mx = mx, mn
    knot_count = int(_clamp(knot_count, 2, 12))
    if abs(mx - mn) < 1e-9:
        return [float(mn)] * knot_count
    span = mx - mn
    knots = []
    upper = _below(2) == 1
    for i in range(knot_count):
        force_low = low_ends and (i == 0 or i == knot_count - 1)
        band = _rf() * 0.18 if force_low else (0.60 + _rf() * 0.40 if upper else _rf() * 0.40)
        knots.append(mn + span * band)
        upper = not upper
    return knots


def sample_profile(knots, t):
    if not knots:
        return 0.0
    if len(knots) == 1:
        return knots[0]
    p = _clamp(t, 0.0, 1.0) * (len(knots) - 1)
    i = min(len(knots) - 2, int(math.floor(p)))
    u = p - i
    smooth = u * u * (3.0 - 2.0 * u)          # C1 smoothstep
    return knots[i] + (knots[i + 1] - knots[i]) * smooth


def _poly_len(pts):
    total = 0.0
    for i in range(1, len(pts)):
        total += math.sqrt((pts[i][0] - pts[i - 1][0]) ** 2 + (pts[i][1] - pts[i - 1][1]) ** 2)
    return total


def windmouse(sx, sy, tx, ty, wind, gravity, curve, profile):
    sqrt3, sqrt5 = math.sqrt(3.0), math.sqrt(5.0)
    x, y = float(sx), float(sy)
    vx = vy = wx = wy = 0.0
    dist0 = max(1.0, math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2))
    if dist0 < 3:
        return [[tx, ty, 0]]
    max_step = _clamp(dist0 / 15.0, 6.0, 30.0)
    stop_radius = min(8.0, max(2.0, dist0 * 0.02))
    pts = []
    guard = 0
    while guard < 2000:
        guard += 1
        dist = math.sqrt((tx - x) ** 2 + (ty - y) ** 2)
        if dist < stop_radius:
            break
        live_wind = wind
        if profile:
            progress = _clamp(1.0 - dist / dist0, 0.0, 1.0)
            live_wind = tuned_wind(dist0, sample_profile(profile, progress) / 100.0)
        wmag = min(live_wind, dist)
        if dist >= stop_radius * 4:             # far: wind roams; near: wind calms
            wx = wx / sqrt3 + (2 * _rf() - 1) * wmag / sqrt5
            wy = wy / sqrt3 + (2 * _rf() - 1) * wmag / sqrt5
        else:
            wx /= sqrt3
            wy /= sqrt3
            max_step = max(2.5, max_step / sqrt5)   # decelerate on approach
        vx += wx + gravity * (tx - x) / dist
        vy += wy + gravity * (ty - y) / dist
        vmag = math.sqrt(vx * vx + vy * vy)
        if vmag > max_step:
            vx = vx / vmag * max_step
            vy = vy / vmag * max_step
        x += vx
        y += vy
        pts.append([int(round(x)), int(round(y)), 0])
    pts.append([tx, ty, 0])                     # land exactly on the target
    return pts


def resample_variable(spine, mn_sp, mx_sp):
    if not spine:
        return []
    if len(spine) == 1:
        return [list(spine[0])]
    if mx_sp < mn_sp:
        mn_sp, mx_sp = mx_sp, mn_sp
    mn_sp = max(0.5, mn_sp)
    mx_sp = max(mn_sp, mx_sp)
    total = _poly_len(spine)
    if total < 1e-6:
        return [list(spine[-1])]
    profile = build_range_profile(mn_sp, mx_sp, 5)
    outp = []
    next_at = sample_profile(profile, 0.0)
    acc = 0.0
    for i in range(1, len(spine)):
        x0, y0 = spine[i - 1][0], spine[i - 1][1]
        seg = math.sqrt((spine[i][0] - x0) ** 2 + (spine[i][1] - y0) ** 2)
        if seg < 1e-6:
            continue
        while acc + seg >= next_at:
            u = (next_at - acc) / seg
            outp.append([int(round(x0 + (spine[i][0] - x0) * u)),
                         int(round(y0 + (spine[i][1] - y0) * u)), 0])
            phase = _clamp(next_at / total, 0.0, 1.0)
            next_at += max(0.5, sample_profile(profile, phase))
        acc += seg
    last = spine[-1]
    if not outp or outp[-1][0] != last[0] or outp[-1][1] != last[1]:
        outp.append([last[0], last[1], 0])
    return outp


def assign_dynamic_delays(pts, sx, sy, smin, smax, target_ms=0):
    """v0.9.8/10 port: per-point delay from a smooth speed profile (low at both ends,
    alternating interior knots), normalized to target_ms when the step set a duration."""
    for p in pts:
        p[2] = 0
    if not pts or (smax <= 0 and target_ms <= 0):
        return
    shape_only = smax <= 0
    lo = 150 if shape_only else max(150, min(smin, smax))
    hi = 2000 if shape_only else max(lo, max(smin, smax))
    knot_count = int(_clamp(4 + len(pts) // 120, 4, 9))
    prof = build_range_profile(float(lo), float(hi), knot_count, low_ends=True)
    segs = []
    path = 0.0
    px, py = sx, sy
    for p in pts:
        s = math.sqrt((p[0] - px) ** 2 + (p[1] - py) ** 2)
        segs.append(s)
        path += s
        px, py = p[0], p[1]
    if path < 1e-6:
        return
    weights = []
    wsum = 0.0
    travelled = 0.0
    for i in range(len(pts)):
        phase = _clamp((travelled + segs[i] * 0.5) / path, 0.0, 1.0)
        speed = _clamp(sample_profile(prof, phase), lo, hi)
        w = segs[i] * 1000.0 / max(1.0, speed)
        weights.append(w)
        wsum += w
        travelled += segs[i]
    if wsum <= 0:
        return
    scale = target_ms / wsum if target_ms > 0 else 1.0
    for i in range(len(pts)):
        pts[i][2] = max(1, int(round(weights[i] * scale)))


def curve_height_ratio(pct):
    p = _clamp(float(pct), 0.0, 200.0)
    if p <= 100.0:
        return 0.08 * ((p / 100.0) ** 1.15)
    return 0.08 + 0.42 * math.sqrt((p - 100.0) / 100.0)


def _ray_to_edge(x, y, dx, dy, w, h, margin):
    max_x = max(margin, w - 1.0 - margin)
    max_y = max(margin, h - 1.0 - margin)
    limit = float("inf")
    if abs(dx) > 1e-9:
        limit = min(limit, (max_x - x) / dx if dx > 0 else (margin - x) / dx)
    if abs(dy) > 1e-9:
        limit = min(limit, (max_y - y) / dy if dy > 0 else (margin - y) / dy)
    return max(0.0, limit) if limit != float("inf") else 0.0


def build_arc(sx, sy, tx, ty, total_ms, cmin, cmax, w, h):
    """v0.9.7/8 port: one continuous half-ellipse; curvature glides through the range;
    the side with screen room is chosen and pre-scaled so no flat clamped sections."""
    dx, dy = tx - sx, ty - sy
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 3:
        return [[tx, ty, max(0, total_ms)]], 0.0, total_ms
    cmin = _clamp(cmin, 0, 200)
    cmax = _clamp(cmax, 0, 200)
    if cmax < cmin:
        cmin, cmax = cmax, cmin
    ux, uy = dx / dist, dy / dist
    nx, ny = -uy, ux
    skew = _rf() * 0.14 - 0.07
    wobble = 0.025 + _rf() * 0.045
    phase0 = _rf() * math.pi * 2.0
    samples = int(_clamp(math.ceil(dist / 12.0), 32, 240))
    knot_count = int(_clamp(4 + int(dist / 320.0), 4, 8))
    knots = build_range_profile(cmin, cmax, knot_count)

    def fit_for_side(side):
        fit = 1.0
        for i in range(1, samples):
            t = i / samples
            q = _clamp(t + skew * math.sin(math.pi * t), 0.0, 1.0)
            along = 0.5 - 0.5 * math.cos(math.pi * q)
            shape = math.sin(math.pi * q) * (1.0 + wobble * math.sin(2.0 * math.pi * t + phase0))
            bx = sx + ux * dist * along
            by = sy + uy * dist * along
            required = dist * curve_height_ratio(sample_profile(knots, t)) * max(0.0, shape)
            if required < 1e-6:
                continue
            room = _ray_to_edge(bx, by, nx * side, ny * side, w, h, 2.0)
            fit = min(fit, room / required)
        return _clamp(fit * 0.94, 0.0, 1.0)

    fit_pos, fit_neg = fit_for_side(+1), fit_for_side(-1)
    if fit_pos >= 0.90 and fit_neg >= 0.90:
        side = -1 if _below(2) == 0 else +1
        fit = fit_pos if side > 0 else fit_neg
    elif fit_pos >= fit_neg:
        side, fit = +1, fit_pos
    else:
        side, fit = -1, fit_neg

    spine = [[sx, sy, 0]]
    actual_height = 0.0
    for i in range(1, samples):
        t = i / samples
        q = _clamp(t + skew * math.sin(math.pi * t), 0.0, 1.0)
        along = 0.5 - 0.5 * math.cos(math.pi * q)
        shape = math.sin(math.pi * q) * (1.0 + wobble * math.sin(2.0 * math.pi * t + phase0))
        local_h = dist * curve_height_ratio(sample_profile(knots, t)) * fit
        normal = side * local_h * max(0.0, shape)
        actual_height = max(actual_height, abs(normal))
        spine.append([int(round(sx + ux * dist * along + nx * normal)),
                      int(round(sy + uy * dist * along + ny * normal)), 0])
    spine.append([tx, ty, 0])
    path_len = _poly_len(spine)
    arc_ms = 0 if total_ms <= 0 else int(_clamp(round(total_ms * max(1.0, path_len / dist)), 60, 30000))
    # memory guard: Pico RAM - only >2500px moves (>4K diagonals) get wider spacing;
    # every screen up to 1440p keeps the hand-matched 2.0-3.2 px gliding steps.
    scale = max(1.0, dist / 2500.0)
    return resample_variable(spine, 2.0 * scale, 3.2 * scale), actual_height, arc_ms


class PausePlanner:
    """Run-scoped pause manager: long distraction breaks once per fresh random cadence."""

    def __init__(self):
        self.moves_since = 0
        self.next_idle_at = -1

    def mid_pause(self, c):
        if c["mid_chance"] > 0 and _below(100) < c["mid_chance"]:
            return rand_range(c["mid_min"], c["mid_max"])
        return 0

    def roll_long(self, c):
        if c["idle_pause_max"] <= 0 or c["idle_every_max"] <= 0:
            return 0
        self.moves_since += 1
        if self.next_idle_at < 0:
            self.next_idle_at = max(1, rand_range(c["idle_every_min"], c["idle_every_max"]))
        if self.moves_since < self.next_idle_at:
            return 0
        self.moves_since = 0
        self.next_idle_at = max(1, rand_range(c["idle_every_min"], c["idle_every_max"]))
        return rand_range(c["idle_pause_min"], c["idle_pause_max"])


_DEFAULT_CFG = dict(before_min=120, before_max=450, after_min=150, after_max=600,
                    mid_chance=12, mid_min=100, mid_max=400,
                    idle_every_min=5, idle_every_max=12, idle_pause_min=1000, idle_pause_max=5000,
                    over_chance=15, curve_min=15, curve_max=45,
                    speed_min=0, speed_max=2000, mt_min=0, mt_max=0)


def plan_move(sx, sy, tx, ty, c, pauses, w, h):
    """Full PlanMove port. Returns dict(before, after, long, pts=[[x,y,delayMs]...])."""
    tx = int(_clamp(tx, 0, max(0, w - 1)))
    ty = int(_clamp(ty, 0, max(0, h - 1)))
    sx = int(_clamp(sx, 0, max(0, w - 1)))
    sy = int(_clamp(sy, 0, max(0, h - 1)))
    dist = math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2)
    speed_lo = max(150, c["speed_min"])
    speed_hi = max(speed_lo, c["speed_max"])
    total_ms = 0 if c["speed_max"] <= 0 else int(_clamp(
        dist * 1000.0 / max(1.0, (speed_lo + speed_hi) / 2.0), 60, 30000))
    curve_min = int(_clamp(c["curve_min"], 0, 200))
    curve_max = int(_clamp(c["curve_max"], 0, 200))
    if curve_max < curve_min:
        curve_min, curve_max = curve_max, curve_min
    sampled = curve_min if curve_max == curve_min else random.randint(curve_min, curve_max)
    curve = _clamp(sampled / 100.0, 0.0, 2.0)
    mt_min, mt_max = max(0, c["mt_min"]), max(0, c["mt_max"])
    if mt_max < mt_min:
        mt_min, mt_max = mt_max, mt_min
    target_ms = rand_range(max(1, mt_min), max(1, mt_max)) if mt_max > 0 else 0

    dense = []
    overshoot_idx = -1
    if curve_max > 100 and dist >= 80:                          # true arc mode
        dense, _height, _arc_ms = build_arc(sx, sy, tx, ty, total_ms, curve_min, curve_max, w, h)
    elif dist >= 60 and c["over_chance"] > 0 and _below(100) < c["over_chance"]:
        ux, uy = (tx - sx) / dist, (ty - sy) / dist
        cscale = min(1.0, curve)
        over = int(_clamp(dist * (0.03 + _rf() * 0.05) * cscale, 2, 20))
        perp = int(_rf() * (2.0 + cscale * 5.0) - (1.0 + cscale * 2.5))
        ox = int(_clamp(tx + int(ux * over - uy * perp), 0, max(0, w - 1)))
        oy = int(_clamp(ty + int(uy * over + ux * perp), 0, max(0, h - 1)))
        leg1_ms = max(40, int(total_ms * 0.8))
        leg2_ms = max(30, total_ms - leg1_ms)
        dense += _build_leg(sx, sy, ox, oy, leg1_ms, curve, curve_min, curve_max)
        overshoot_idx = len(dense) - 1
        dense += _build_leg(ox, oy, tx, ty, leg2_ms, curve, curve_min, curve_max)
    else:
        dense = _build_leg(sx, sy, tx, ty, total_ms, curve, curve_min, curve_max)

    for p in dense:                                             # keep on-screen
        p[0] = int(_clamp(p[0], 0, max(0, w - 1)))
        p[1] = int(_clamp(p[1], 0, max(0, h - 1)))

    assign_dynamic_delays(dense, sx, sy, c["speed_min"], c["speed_max"], target_ms)

    if overshoot_idx >= 0:                                      # re-aim pause
        dense[overshoot_idx][2] += rand_range(60, 180)
    mid = pauses.mid_pause(c)                                   # one hesitation per move
    if mid > 0 and len(dense) >= 8:
        dense[2 + _below(len(dense) - 4)][2] += mid

    return {"before": rand_range(c["before_min"], c["before_max"]),
            "after": rand_range(c["after_min"], c["after_max"]),
            "long": pauses.roll_long(c),
            "target": (tx, ty),
            "pts": dense}


def _build_leg(sx, sy, tx, ty, total_ms, curve, cmin, cmax):
    dist0 = max(1.0, math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2))
    profile = None
    if cmin >= 0 and cmax >= 0:
        profile = build_range_profile(cmin, cmax, int(_clamp(4 + int(dist0 / 320.0), 4, 8)))
    spine = windmouse(sx, sy, tx, ty, tuned_wind(dist0, curve), 14.0, curve, profile)
    with_start = [[sx, sy, 0]] + spine
    scale = max(1.0, dist0 / 2500.0)                           # Pico RAM guard (>4K only)
    return resample_variable(with_start, 2.0 * scale, 3.2 * scale)


# ── typing port (C# TypeTextCommands v0.9.15 → Python) ──────────────────────────────────

_QWERTY_ROWS = ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm")
_PUNCT = ".,!?;:"


def _qwerty_neighbor(ch):
    lower = ch.lower()
    for row in _QWERTY_ROWS:
        i = row.find(lower)
        if i < 0:
            continue
        j = i + (-1 if _below(2) == 0 else 1)
        if j < 0 or j >= len(row):
            j = 1 if i == 0 else i - 1
        n = row[j]
        return n.upper() if ch.isupper() else n
    return None


def _split_punct(s):
    outp = []
    start = 0

    for i in range(len(s) - 1):
        if s[i] in _PUNCT:
            outp.append(s[start:i + 1])
            start = i + 1
    if start < len(s):
        outp.append(s[start:])
    if not outp and s:
        outp.append(s)
    return outp


def plan_typing(text, p):
    """Returns [("KTEXT",hmin,hmax,chunk) | ("DLY",ms) | ("KCOMBO",vk), ...].
    p keys: h,w (ms ranges), wp (word pause chance %), p (punct pause range),
    think ((chance,(mn,mx))), typo ((mn,mx) cadence, 0/0=off)."""
    hmin, hmax = p.get("h", (80, 220))
    wmin, wmax = p.get("w", (0, 0))
    wp = _clamp(p.get("wp", 100), 0, 100)
    pmin, pmax = p.get("p", (0, 0))
    think_chance, think_range = p.get("think", (0, (800, 2200)))
    think_chance = _clamp(think_chance, 0, 100)
    think_min, think_max = think_range
    typo_min, typo_max = p.get("typo", (0, 0))
    typo_cadence = typo_max > 0
    next_typo_at = max(1, rand_range(typo_min, typo_max)) if typo_cadence else -1
    words_since_typo = 0
    word_mode = wmax > 0 or pmax > 0 or think_chance > 0 or typo_cadence

    cmds = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    pending = []

    def flush():
        s = "".join(pending)
        pending.clear()
        for i in range(0, len(s), 60):
            cmds.append(("KTEXT", hmin, hmax, s[i:i + 60]))

    for li, line in enumerate(lines):
        if word_mode:
            words = [wd for wd in line.split() if wd]
            for wi, word in enumerate(words):
                tail = " " if wi < len(words) - 1 else ""
                typed = word + tail
                typo_due = typo_cadence and (words_since_typo := words_since_typo + 1) >= next_typo_at
                if typo_due and 2 <= len(word) <= 60:
                    pos = 1 + _below(len(word) - 1)      # never the first char
                    wrong = _qwerty_neighbor(word[pos])
                    if wrong is not None:
                        flush()
                        cmds.append(("KTEXT", hmin, hmax, word[:pos] + wrong))
                        cmds.append(("DLY", rand_range(max(hmax, 120), hmax * 2 + 200)))
                        cmds.append(("KCOMBO", 8))       # Backspace
                        cmds.append(("DLY", rand_range(hmin, hmax)))
                        typed = word[pos:] + tail
                        words_since_typo = 0
                        next_typo_at = max(1, rand_range(typo_min, typo_max))
                segs = _split_punct(typed) if pmax > 0 else [typed]
                for si, seg in enumerate(segs):
                    pending.append(seg)
                    if si < len(segs) - 1:
                        flush()
                        cmds.append(("DLY", rand_range(pmin, pmax)))
                if wi < len(words) - 1:
                    if wmax > 0 and _below(100) < wp:
                        flush()
                        cmds.append(("DLY", rand_range(wmin, wmax)))
                    if think_chance > 0 and think_max > 0 and _below(100) < think_chance:
                        flush()
                        cmds.append(("DLY", rand_range(think_min, think_max)))
            flush()
        else:
            for i in range(0, len(line), 60):
                cmds.append(("KTEXT", hmin, hmax, line[i:i + 60]))
        if li < len(lines) - 1:
            cmds.append(("KCOMBO", 13))                  # Enter between lines
    return cmds


# ── executor ─────────────────────────────────────────────────────────────────────────────

def run_plan(ops, ctx):
    """Executes parsed ops against ctx. ctx provides:
    now()->float seconds, sleep_ms(ms)->bool(False=abort), mmove(x,y),
    mclick(btn,n,hmin,hmax), ktext(hmin,hmax,text), kcombo(vk),
    wait_light(lo,hi,stable,to,mode)->bool, key(vk,hold_ms), log(msg),
    screen_w, screen_h, speed_min, speed_max."""
    pauses = PausePlanner()
    pos = _load_mouse_pos(ctx, ops)
    i = 0
    stack = []          # [start_index, remaining(0=forever), deadline_or_None]
    while i < len(ops):
        op, prm = ops[i]
        if op == "PLAN":
            pass
        elif op == "SCREEN":
            ctx.screen_w, ctx.screen_h = prm["v"]
            pos[0] = _clamp(pos[0], 0, max(0, ctx.screen_w - 1))
            pos[1] = _clamp(pos[1], 0, max(0, ctx.screen_h - 1))
            _save_mouse_pos(ctx, pos)
        elif op == "SPEED":
            ctx.speed_min, ctx.speed_max = prm["v"]
        elif op == "DELAY":
            if not ctx.sleep_ms(rand_range(*prm["v"])):
                raise PlanAbort()
        elif op == "LOOP":
            stack.append([i, prm["n"], None])
        elif op == "LOOPTIME":
            stack.append([i, 0, ctx.now() + prm["sec"]])
        elif op == "ENDLOOP":
            top = stack[-1]
            if top[2] is not None:                       # LOOPTIME
                if ctx.now() < top[2]:
                    i = top[0]
                else:
                    stack.pop()
            elif top[1] == 0:                            # forever
                i = top[0]
            else:
                top[1] -= 1
                if top[1] > 0:
                    i = top[0]
                else:
                    stack.pop()
        elif op == "RMOUSE":
            _exec_rmouse(prm, ctx, pauses, pos)
        elif op == "CLICK":
            hold = prm.get("hold", (0, 0))
            ctx.mclick(prm["btn"], prm["n"], hold[0], hold[1])
        elif op == "TYPE":
            for cmd in plan_typing(prm["text"], prm):
                if cmd[0] == "KTEXT":
                    ctx.ktext(cmd[1], cmd[2], cmd[3])
                elif cmd[0] == "DLY":
                    if not ctx.sleep_ms(cmd[1]):
                        raise PlanAbort()
                else:
                    ctx.kcombo(cmd[1])
        elif op == "WLIGHT":
            ok = ctx.wait_light(prm["lo"], prm["hi"], prm["stable"], prm["to"], prm["mode"])
            if ok and "key" in prm:
                vk, hmn, hmx = prm["key"]
                rmn, rmx = prm.get("react", (80, 180))
                if not ctx.sleep_ms(rand_range(rmn, rmx)):
                    raise PlanAbort()
                ctx.key(vk, rand_range(hmn, hmx))
            ctx.log("wlight " + ("match" if ok else "timeout"))
        i += 1



def _exec_rmouse(prm, ctx, pauses, pos):
    rx, ry, rw, rh = prm["region"]
    c = dict(_DEFAULT_CFG)
    c["speed_min"], c["speed_max"] = ctx.speed_min, ctx.speed_max
    if "mt" in prm:
        c["mt_min"], c["mt_max"] = prm["mt"]
    if "curve" in prm:
        c["curve_min"], c["curve_max"] = prm["curve"]
    if "before" in prm:
        c["before_min"], c["before_max"] = prm["before"]
    if "after" in prm:
        c["after_min"], c["after_max"] = prm["after"]
    if "mid" in prm:
        c["mid_chance"], (c["mid_min"], c["mid_max"]) = prm["mid"]
    if "idle" in prm:
        (c["idle_every_min"], c["idle_every_max"]), (c["idle_pause_min"], c["idle_pause_max"]) = prm["idle"]
    if "over" in prm:
        c["over_chance"] = prm["over"]
    tx = random.randint(rx, rx + max(0, rw - 1))
    ty = random.randint(ry, ry + max(0, rh - 1))
    plan = plan_move(pos[0], pos[1], tx, ty, c, pauses, ctx.screen_w, ctx.screen_h)
    ctx.log("rmouse -> (%d,%d) %d pts" % (tx, ty, len(plan["pts"])))
    if not ctx.sleep_ms(plan["before"]):
        raise PlanAbort()
    for pt in plan["pts"]:
        ctx.mmove(pt[0], pt[1])
        # Persist immediately, before the abortable delay: Stop in the middle of
        # a path resumes from the last point that was actually sent to the arm.
        pos[0], pos[1] = pt[0], pt[1]
        _save_mouse_pos(ctx, pos)
        if not ctx.sleep_ms(pt[2]):
            raise PlanAbort()
    pos[0], pos[1] = plan["target"]
    _save_mouse_pos(ctx, pos)
    if not ctx.sleep_ms(plan["after"]):
        raise PlanAbort()
    if plan["long"] > 0:
        ctx.log("idle break %d ms" % plan["long"])
        if not ctx.sleep_ms(plan["long"]):
            raise PlanAbort()

"""";
}
