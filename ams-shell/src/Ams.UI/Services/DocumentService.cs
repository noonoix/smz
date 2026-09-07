using System.IO;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// .amsj document persistence (phase F5): a versioned JSON envelope around the
/// step tree. StepNode serializes its Props dictionary verbatim, so new step
/// fields survive open/save even before the UI knows about them.
/// </summary>
public static class DocumentService
{
    private sealed class Doc
    {
        public string app { get; set; } = "AMS";
        public string version { get; set; } = "0.8.2";
        public List<StepNode> steps { get; set; } = new();
    }

    private static readonly JsonSerializerOptions Opts = new() { WriteIndented = true };

    public static void Save(string path, IEnumerable<StepNode> roots)
    {
        var doc = new Doc { steps = roots.ToList() };
        File.WriteAllText(path, JsonSerializer.Serialize(doc, Opts));
    }

    public static List<StepNode> Load(string path)
    {
        var doc = JsonSerializer.Deserialize<Doc>(File.ReadAllText(path))
                  ?? throw new InvalidDataException("Not an AMS document.");
        if (doc.app != "AMS") throw new InvalidDataException("Not an AMS document.");
        foreach (var n in doc.steps) FixParents(n, null);
        return doc.steps;
    }

    /// <summary>
    /// v0.9.42 - a conditionless findImage / waitForSound / waitForLight can never own a
    /// branch. Older plans (and pre-v0.9.42 edits) nested steps under such a head, so those
    /// rows rendered one indent level too deep and pretended to be a Then branch. Lift every
    /// orphan child out so it becomes the next sibling of the step, order preserved.
    /// Else marker rows keep their children - they are the real not-found branch.
    /// Returns the number of lifted rows.
    /// </summary>
    public static int LiftOrphanChildren(IList<StepNode> list, StepNode? parent = null)
    {
        int lifted = 0;
        for (int i = 0; i < list.Count; i++)
        {
            var n = list[i];
            lifted += LiftOrphanChildren(n.Children, n);
            if (n.Children.Count == 0 || StepDefinitions.AcceptsChildren(n) || IsBranchMarker(n)) continue;
            var orphans = n.Children.ToList();
            n.Children.Clear();
            int at = i + 1;
            foreach (var c in orphans)
            {
                c.Parent = parent;
                list.Insert(at++, c);
                lifted++;
            }
            i = at - 1;
        }
        return lifted;
    }

    /// <summary>Else / End If comment markers are structural: they legitimately hold children.</summary>
    private static bool IsBranchMarker(StepNode n)
        => n.Type == "comment"
           && (PropEx.GetString(n.Props, "text").StartsWith("Else", System.StringComparison.Ordinal)
               || PropEx.GetString(n.Props, "text").StartsWith("End If", System.StringComparison.Ordinal));

    internal static void FixParents(StepNode n, StepNode? parent)
    {
        n.Parent = parent;   // Parent is [JsonIgnore] — rebuilt here
        foreach (var c in n.Children) FixParents(c, n);
    }
}

/// <summary>
/// App options (Tools → Options → Serial/Board tab, §2.4). Persisted to
/// ams-settings.json next to the exe.
/// </summary>
public sealed class AppSettings
{
    /// <summary>Default AUTO: BoardLink scans KNOWN_VIDS and finds the board on any COM (§14.3 / §15.5).</summary>
    public string Port { get; set; } = "AUTO";
    public string PythonDir { get; set; } = "";
    public string ToolkitDir { get; set; } = "";

    // Play Options (AMK bottom-panel parity, §9.1): app-side run settings — never in the .amsj
    public string PlayRepeatMode { get; set; } = "once";      // once | times | timed
    public int PlayRepeatTimes { get; set; } = 10;
    public int PlayRepeatValue { get; set; } = 1;
    public string PlayRepeatUnit { get; set; } = "minute";    // second | minute | hour
    public bool ShutdownWhenFinished { get; set; }
    public bool NoActivateWhenStopped { get; set; }
    // Word-level humanize defaults for typeText steps (§v0.8.4)
    public int WordDelayMin { get; set; }
    public int WordDelayMax { get; set; }
    // Human-like mouse movement: random delay after MMOVE proportional to distance (§v0.8.5)
    // speed range in px/s — 0/0 = disabled (firmware-paced move).
    // v0.9.24: recalibrated from the user's DENSE hand recording (6,269 samples, ≥40 ms
    // windows): travel speed p25 ≈ 416, median ≈ 980, p75 ≈ 1970 px/s. The v0.9.23
    // range (150–500) came from a coarsely-sampled export and ran 2–6× slower than the real hand.
    public int MouseMoveSpeedMin { get; set; } = 300;
    public int MouseMoveSpeedMax { get; set; } = 2000;
    // v0.9.23 — personal typing cadence from Options → "Measure from my hand"; used as the
    // Type Text fallback when a step omits hmin/hmax. Human-calibrated default 80–220 ms.
    public int TypeKeyMinMs { get; set; } = 80;
    public int TypeKeyMaxMs { get; set; } = 220;
    // Hotkey bindings (saved as "Key + Modifiers" strings, §v0.8.5)
    public string RunHotkey { get; set; } = "Shift+F1";      // legacy — migrated into RunStopHotkey (v0.9.43)
    public string StopHotkey { get; set; } = "Shift+F2";     // legacy — stop now shares the run key
    public string PauseHotkey { get; set; } = "Shift+F3";    // legacy — migrated into PauseResumeHotkey
    public string ResumeHotkey { get; set; } = "Shift+F4";   // legacy — resume now shares the pause key
    // v0.9.43 — paired playback hotkeys (user request: 4 keys → 2). Empty until migrated in Load().
    public string RunStopHotkey { get; set; } = "";
    public string PauseResumeHotkey { get; set; } = "";
    // v0.9.44 — flexible role split: which board executes keyboard commands ("pico" = the brain, "promicro" = the arm).
    public string KeyboardBoard { get; set; } = "pico";

    private static string Path_ => System.IO.Path.Combine(AppContext.BaseDirectory, "ams-settings.json");

    /// <summary>v0.9.23/v0.9.24 — migrate the untouched factory speed range (0/2300) to the
    /// CURRENT human default (150/500 in v0.9.23, 300/2000 since v0.9.24); custom values and
    /// the deliberate 0/0 are preserved. Pure method so TestRunner can drive the matrix.</summary>
    public static (int min, int max) NormalizeSpeedDefaults(int min, int max)
        => min == 0 && max == 2300 ? (300, 2000) : (min, max);

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(Path_))
            {
                var s = JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(Path_)) ?? new();
                // v0.9.23 — one-time migration of the untouched factory speed range
                var (m0, m1) = NormalizeSpeedDefaults(s.MouseMoveSpeedMin, s.MouseMoveSpeedMax);
                if (m0 != s.MouseMoveSpeedMin || m1 != s.MouseMoveSpeedMax)
                {
                    s.MouseMoveSpeedMin = m0;
                    s.MouseMoveSpeedMax = m1;
                    s.Save();
                }
                // v0.9.43 — one-time migration to the paired hotkeys: run/stop take the old run key,
                // pause/resume take the old pause key; the old stop/resume keys are retired.
                if (string.IsNullOrWhiteSpace(s.RunStopHotkey))
                {
                    s.RunStopHotkey = s.RunHotkey;
                    s.PauseResumeHotkey = s.PauseHotkey;
                    s.Save();
                }
                // v0.9.57 — sanitize stale paths from another machine
                if (!string.IsNullOrEmpty(s.PythonDir) && !System.IO.Directory.Exists(s.PythonDir))
                {
                    s.PythonDir = "";
                    s.Save();
                }
                if (!string.IsNullOrEmpty(s.ToolkitDir) && !System.IO.Directory.Exists(s.ToolkitDir))
                {
                    s.ToolkitDir = "";
                    s.Save();
                }
                if (s.Port != "AUTO" && !System.IO.Ports.SerialPort.GetPortNames().Contains(s.Port))
                {
                    s.Port = "AUTO";
                    s.Save();
                }
                return s;
            }
        }
        catch { /* corrupt settings → defaults */ }
        return new();
    }

    public void Save() => File.WriteAllText(Path_, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
}
