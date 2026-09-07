using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Import .amk (design doc §9.4): runs the amk_toolkit decoder
/// (python amk_decoder.py file.amk --json out.json --imgdir dir) and maps the
/// decoded records onto the AMS step model.
///
/// TYPE mapping verified against the toolkit's sample decodes (daroon1/keyboard/
/// mouse/right/openfile/pic/sound — see BUILD-LOG and the mirror test):
///   2 findImage · 5 mouseClick · 12 mouseMove · 14 mouseScroll/event ·
///   15 keystroke · 17/18 keyDown/keyUp · 24 delay · 32 randomMousePosition ·
///   8 forLoop (sub = body) · 9 Next → comment marker · 6 Else → comment note ·
///   7 End If → comment marker · 23 playScript · 34 callFunction → typeText / openFile
///
/// Notes:
///  • DIS / IF / ATM are NUMBERS (0/1) in the decoder JSON — read them with
///    GetInt(...)==1, never JsonElement.GetBoolean() (throws on numbers).
///  • ATM is the park-cursor checkbox (§9.5) — it does NOT mean "never timeout";
///    never-timeout is TOUT == -1.
///  • Images extract to a persistent folder next to the .amk (&lt;name&gt;_images) —
///    findImage steps reference those PNGs at run time, so a temp dir is wrong.
///  • v0.8.2 — the python decoder does NOT reliably extract Search Picture images
///    (user report), so AmkImageExtractor parses the .amk binary natively (BMPN =
///    W/H/32bpp + BGRA pixels) and case 2 falls back to those PNGs in pre-order.
///    ATM (park cursor) and CMT (picture comment) now map to real props.
/// </summary>
public static class AmkImporter
{
    public sealed class ImportResult
    {
        public IReadOnlyList<StepNode> Roots { get; init; } = Array.Empty<StepNode>();
        public IReadOnlyList<string> Warnings { get; init; } = Array.Empty<string>();
    }

    /// <summary>Decode a .amk file into a step tree. Throws (with the decoder's
    /// stderr) on hard failure — both call sites (ImportAmk command, RunEngine
    /// playScript) catch and surface it.</summary>
    public static ImportResult Import(string amkPath, string? toolkitDir)
    {
        if (!File.Exists(amkPath)) throw new FileNotFoundException(amkPath);

        string? decoder = null;
        if (!string.IsNullOrWhiteSpace(toolkitDir) && File.Exists(Path.Combine(toolkitDir, "amk_decoder.py")))
            decoder = Path.Combine(toolkitDir, "amk_decoder.py");
        else if (File.Exists("amk_decoder.py"))
            decoder = Path.GetFullPath("amk_decoder.py");
        if (decoder is null)
            throw new FileNotFoundException(
                "amk_decoder.py not found — set the AMK toolkit folder in Tools → Options.");

        var imgDir = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(amkPath))!,
                                  Path.GetFileNameWithoutExtension(amkPath) + "_images");
        var jsonFile = Path.Combine(Path.GetTempPath(), "ams_import_" + Guid.NewGuid().ToString("N") + ".json");

        var psi = new ProcessStartInfo("python")
        {
            RedirectStandardOutput = true,
            StandardOutputEncoding = Encoding.UTF8,
            RedirectStandardError = true,
            StandardErrorEncoding = Encoding.UTF8,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        psi.ArgumentList.Add(decoder);
        psi.ArgumentList.Add(amkPath);
        psi.ArgumentList.Add("--json");
        psi.ArgumentList.Add(jsonFile);
        psi.ArgumentList.Add("--imgdir");
        psi.ArgumentList.Add(imgDir);

        var p = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start python.");
        // Read stdout + stderr concurrently to avoid pipe-buffer deadlock:
        // the decoder emits ~12 KB of Persian text to stdout which would fill
        // the OS pipe (≈4 KB) and block the child if nobody reads it.
        using var tOut = new CancellationTokenSource(65_000);
        using var tErr = new CancellationTokenSource(65_000);
        var outTask = p.StandardOutput.ReadToEndAsync().WaitAsync(tOut.Token);
        var errTask = p.StandardError.ReadToEndAsync().WaitAsync(tErr.Token);
        p.WaitForExit(60_000);
        string stdout = outTask.IsCompletedSuccessfully ? outTask.Result : "";
        string stderr = errTask.IsCompletedSuccessfully ? errTask.Result : "";
        if (p.ExitCode != 0 || !File.Exists(jsonFile))
            throw new InvalidOperationException("amk_decoder failed (exit " + p.ExitCode + "): " + stderr.Trim());

        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(jsonFile));
            var warnings = new List<string>();
            // v0.8.2 — native embedded-picture extraction (the missing puzzle piece):
            // TYPE 2 records carry the picture as BMPN (W/H/32bpp + BGRA pixels).
            // File order == the pre-order in which TYPE 2 records are mapped below.
            var nativeImages = AmkImageExtractor.ExtractImages(amkPath, imgDir, m => warnings.Add(m));
            if (nativeImages.Count > 0)
                warnings.Add($"native extractor: {nativeImages.Count} embedded picture(s) → {Path.GetFileName(imgDir)}/");
            var imgIdx = new int[1];
            var roots = MapRecords(doc.RootElement.GetProperty("records"), imgDir, warnings, nativeImages, imgIdx);
            return new ImportResult { Roots = roots, Warnings = warnings };
        }
        finally
        {
            try { File.Delete(jsonFile); } catch { }
        }
    }

    // ─────────────────────────── mapping ───────────────────────────

    private static List<StepNode> MapRecords(JsonElement records, string imgdir, List<string> warnings,
        IReadOnlyList<string>? nativeImages = null, int[]? imgIdx = null)
    {
        var list = new List<StepNode>();
        foreach (var r in records.EnumerateArray())
        {
            var node = MapRecord(r, imgdir, warnings, nativeImages, imgIdx);
            if (node is null) continue;
            list.Add(node);
        }
        return list;
    }

    private static StepNode? MapRecord(JsonElement r, string imgdir, List<string> warnings,
        IReadOnlyList<string>? nativeImages = null, int[]? imgIdx = null)
    {
        int type = GetInt(r, "TYPE");
        StepNode? node;

        switch (type)
        {
            case 2:   // Search Picture (§3.3.1)
            {
                int tout = GetInt(r, "TOUT");
                bool never = tout < 0;
                // v0.8.2 — pictures: decoder path first; when it left no usable file, fall back
                // to the native BMPN extraction at the same pre-order position. ATM/CMT map to
                // real props now (parkCursor / picComment — the dialog already reads them).
                var pics = ResolveImage(r, imgdir);
                bool decoderPicOk = pics.Length > 0 && File.Exists(pics.Split('\n')[0]);
                if (!decoderPicOk && nativeImages is not null && imgIdx is not null && imgIdx[0] < nativeImages.Count)
                {
                    pics = nativeImages[imgIdx[0]];
                    warnings.Add("find image: decoder left no usable picture — used the native BMPN extraction");
                }
                if (imgIdx is not null) imgIdx[0]++;   // advance per TYPE 2 — keeps pre-order correspondence
                node = New("findImage", r,
                    ("pictures", pics),
                    ("parkCursor", Flag(r, "ATM")),
                    ("picComment", GetStr(r, "CMT")),
                    ("similarity", GetInt(r, "SML", 75)),
                    ("searchScope", GetStr(r, "WHER") switch { "rg" => "region", "cur" => "fromCursor", _ => "entireScreen" }),
                    ("x", GetInt(r, "RGNL")), ("y", GetInt(r, "RGNT")),
                    ("w", Math.Max(1, GetInt(r, "RGNR") - GetInt(r, "RGNL"))),
                    ("h", Math.Max(1, GetInt(r, "RGNB") - GetInt(r, "RGNT"))),
                    ("neverTimeout", never),
                    ("timeoutValue", never ? 3 : Math.Max(0, tout)),
                    ("timeoutUnit", GetStr(r, "TUNT") switch { "sec" => "second", "min" => "minute", "hour" => "hour", _ => "ms" }),
                    ("onFound", GetStr(r, "FDO") switch
                    {
                        "move click" => "moveAndClick",
                        "move" => "moveOnly",
                        "click no move" => "clickRestoreCursor",   // §3.3.1 option B
                        _ => "none",
                    }),
                    ("onTimeout", GetStr(r, "TDO") switch
                    {
                        "stop tip" => "stopWithTip",
                        "stop no tip" => "stopSilent",
                        _ => "continue",
                    }),
                    ("insertIfElse", Flag(r, "IF")));
                break;
            }

            case 5:   // Mouse Click — unified dialog (§5.5.1)
                node = New("mouseClick", r,
                    ("button", GetInt(r, "MBTN") switch { 1 => "middle", 2 => "right", _ => "left" }),
                    ("action", GetInt(r, "CLKT") == 1 ? "double" : "single"));
                break;

            case 12:  // Mouse Position — XPOS/YPOS are expressions in AMK (§9.3)
            {
                var xs = GetStr(r, "XPOS"); var ys = GetStr(r, "YPOS");
                int x = GetInt(r, "XPOS"); int y = GetInt(r, "YPOS");
                node = New("mouseMove", r, ("x", x), ("y", y), ("human", true));
                if ((x == 0 && xs.Length > 0 && xs != "0") || (y == 0 && ys.Length > 0 && ys != "0"))
                {
                    node.Name = (node.Name + "  [expr: " + xs + ", " + ys + "]").Trim();
                    warnings.Add($"mouse position expression '{xs},{ys}' imported as fixed 0,0 — see step name");
                }
                break;
            }

            case 14:  // Mouse Event / Scroll (§9.2: EVT 7 = Scroll Down, 4 = Right Up)
                if (GetInt(r, "EVT") == 7)
                    node = New("mouseScroll", r, ("delta", -Math.Max(1, GetInt(r, "SCRL", 120) / 120)));
                else if (GetInt(r, "EVT") == 4)
                    node = New("rawCommand", r, ("cmd", "MUP|right"));
                else
                {
                    warnings.Add($"mouse event EVT={GetInt(r, "EVT")} not mapped — imported as comment");
                    node = New("comment", r, ("text", $"mouse event EVT={GetInt(r, "EVT")} SCRL={GetInt(r, "SCRL")} (not mapped)"));
                }
                break;

            case 15:  // Keystroke — VK codes (§9.3)
                node = New("keystroke", r,
                    ("modCtrl", Flag(r, "CTRL")), ("modShift", Flag(r, "SHFT")),
                    ("modAlt", Flag(r, "ALT")), ("modWin", Flag(r, "WIN")),
                    ("key", VkName(GetInt(r, "KEY"), warnings)));
                break;

            case 17:  node = New("keyDown", r, ("key", VkName(GetInt(r, "KEY"), warnings))); break;
            case 18:  node = New("keyUp", r, ("key", VkName(GetInt(r, "KEY"), warnings))); break;

            case 24:  // Delay — random range (§4, v0.7)
                node = New("delay", r,
                    ("minMs", GetInt(r, "wait_min")), ("maxMs", GetInt(r, "wait_ms", 333)));
                break;

            case 32:  // Random Mouse Position — region edges (§9.2)
                node = New("randomMousePosition", r,
                    ("x", GetInt(r, "RGNL")), ("y", GetInt(r, "RGNT")),
                    ("w", Math.Max(1, GetInt(r, "RGNR") - GetInt(r, "RGNL"))),
                    ("h", Math.Max(1, GetInt(r, "RGNB") - GetInt(r, "RGNT"))));
                break;

            case 8:   // For Loop — LPTP 0=count(TO) 1=time(TIME string) 2=infinite (§9.2)
            {
                var timeParts = GetStr(r, "TIME").Split(' ', StringSplitOptions.RemoveEmptyEntries);
                int timeValue = timeParts.Length > 0 && int.TryParse(timeParts[0], out var tv) ? tv : 10;
                string timeUnit = timeParts.Length > 1 ? timeParts[1] : "minute";
                if (timeUnit is not ("second" or "minute" or "hour")) timeUnit = "minute";
                node = New("forLoop", r,
                    ("mode", GetInt(r, "LPTP") switch { 0 => "count", 1 => "time", _ => "infinite" }),
                    ("count", Math.Max(1, GetInt(r, "TO", 10))),
                    ("timeValue", timeValue), ("timeUnit", timeUnit));
                break;
            }

            case 9:   // Next — AMK shows it as a tree row; keep as a marker comment
                node = New("comment", r, ("text", "Next"));
                break;

            case 6:   // Else — branch lives in this record's sub (§9.2)
            {
                // v0.6.3 — branch steps are PRESERVED as children of this note row
                // (previously dropped). They are not executed as a branch yet:
                // comment is not a container, so RunEngine never walks into them.
                int n = r.TryGetProperty("sub", out var sub) ? sub.GetArrayLength() : 0;
                node = New("comment", r, ("text", n > 0
                    ? $"Else — {n} step(s) preserved below; branch execution lands later"
                    : "Else"));
                if (n > 0)
                    warnings.Add($"Else branch with {n} step(s) preserved under the note row (branch execution lands later)");
                break;
            }

            case 7:   // End If — marker comment (AMK tree parity)
                node = New("comment", r, ("text", "End If"));
                break;

            case 23:  // Play Another Script (Master Script pattern, §9.5)
                node = New("playScript", r, ("path", GetStr(r, "FILE")));
                break;

            case 34:  // Call Function — TypeText / ExecuteFile (§5.5.6)
            {
                var op = "";
                if (r.TryGetProperty("code", out var code)
                    && code.TryGetProperty("ops", out var ops)
                    && ops.GetArrayLength() > 0)
                    op = ops[0].GetString() ?? "";

                if (op.StartsWith("TypeText(", StringComparison.Ordinal))
                {
                    bool clip = op.Contains(", True") || op.Contains(",True");
                    node = New("typeText", r,
                        ("text", FirstQuoted(op)), ("mode", clip ? "clipboard" : "keystrokes"));
                }
                else if (op.StartsWith("ExecuteFile(", StringComparison.Ordinal))
                {
                    node = New("openFile", r,
                        ("path", FirstQuoted(op)), ("args", ""), ("windowState", "normal"));
                }
                else
                {
                    warnings.Add("Call Function not mapped: " + Truncate(op, 80));
                    node = New("comment", r, ("text", "Call: " + op));
                }
                break;
            }

            default:
                warnings.Add($"TYPE {type} not supported — imported as comment");
                node = New("comment", r, ("text", $"Unsupported AMK record TYPE={type}"));
                break;
        }

        // nested records (loop body / Then branch / Else branch — §9.2 SUB)
        if (node is not null && type is 2 or 8 or 6 && r.TryGetProperty("sub", out var subEl))
            foreach (var child in MapRecords(subEl, imgdir, warnings, nativeImages, imgIdx))
            {
                child.Parent = node;
                node.Children.Add(child);
            }

        return node;
    }

    // ─────────────────────────── helpers ───────────────────────────

    private static StepNode New(string type, JsonElement r, params (string Key, object? Val)[] props)
    {
        var node = new StepNode
        {
            Type = type,
            Name = GetStr(r, "NAME"),
            Delay = GetInt(r, "DLY"),
            IsDisabled = Flag(r, "DIS"),
        };
        foreach (var (k, v) in props) node.Props[k] = v;
        node.RefreshSummary();
        return node;
    }

    private static string ResolveImage(JsonElement r, string imgdir)
    {
        if (!r.TryGetProperty("image", out var img)) return "";
        // object form: { "file": "name.png" }
        if (img.ValueKind == JsonValueKind.Object && img.TryGetProperty("file", out var f))
        {
            var name = f.GetString();
            if (!string.IsNullOrEmpty(name)) return Path.Combine(imgdir, name);
        }
        // v0.8.2 — tolerate the array form too (multi-picture OR lists):
        // ["a.png", …] or [{ "file": "a.png" }, …] → one path per line (the dialog's format)
        if (img.ValueKind == JsonValueKind.Array)
        {
            var names = new List<string>();
            foreach (var it in img.EnumerateArray())
            {
                string? n = it.ValueKind == JsonValueKind.Object && it.TryGetProperty("file", out var ff)
                    ? ff.GetString() : it.GetString();
                if (!string.IsNullOrEmpty(n)) names.Add(Path.Combine(imgdir, n));
            }
            return string.Join('\n', names);
        }
        return "";
    }

    private static string VkName(int vk, List<string> warnings)
    {
        if (VkToName.TryGetValue(vk, out var name)) return name;
        warnings.Add($"unknown VK code {vk} — mapped to F4 (edit the step to fix)");
        return "F4";
    }

    private static string FirstQuoted(string s)
    {
        var m = Regex.Match(s, "'((?:[^']|'')*)'");
        return m.Success ? m.Groups[1].Value.Replace("''", "'") : "";
    }

    private static string Truncate(string s, int n) => s.Length <= n ? s : s[..n] + "…";

    /// <summary>Number-safe int read: handles Number, numeric String, and Bool.</summary>
    private static int GetInt(JsonElement r, string key, int fallback = 0)
    {
        if (!r.TryGetProperty(key, out var v)) return fallback;
        return v.ValueKind switch
        {
            JsonValueKind.Number => v.TryGetInt32(out var i) ? i : (int)v.GetDouble(),
            JsonValueKind.String => int.TryParse(v.GetString(), out var i) ? i
                : double.TryParse(v.GetString(), out var d2) ? (int)d2 : fallback,
            JsonValueKind.True => 1,
            JsonValueKind.False => 0,
            _ => fallback,
        };
    }

    /// <summary>DIS/IF/ATM are NUMBERS (0/1) in the decoder JSON — never GetBoolean() them.</summary>
    private static bool Flag(JsonElement r, string key)
    {
        if (!r.TryGetProperty(key, out var v)) return false;
        return v.ValueKind switch
        {
            JsonValueKind.Number => v.TryGetInt32(out var i) && i == 1,
            JsonValueKind.True => true,
            JsonValueKind.String => v.GetString() == "1",
            _ => false,
        };
    }

    private static string GetStr(JsonElement r, string key)
    {
        if (!r.TryGetProperty(key, out var v)) return "";
        return v.ValueKind switch
        {
            JsonValueKind.String => v.GetString() ?? "",
            JsonValueKind.Number => v.ToString(),
            _ => "",
        };
    }

    /// <summary>VK → AMK display name, built from the same table the dialogs use.</summary>
    private static readonly IReadOnlyDictionary<int, string> VkToName = BuildReverse();

    private static IReadOnlyDictionary<int, string> BuildReverse()
    {
        var map = new Dictionary<int, string>();
        foreach (var kv in KeyMap.VK)
            if (!map.ContainsKey(kv.Value)) map[kv.Value] = kv.Key;
        return map;
    }
}
