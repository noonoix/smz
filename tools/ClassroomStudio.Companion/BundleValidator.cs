using System.Security.Cryptography;
using System.Text.Json.Nodes;

namespace ClassroomStudio.Companion;

public static class BundleValidator
{
    public static readonly string[] RequiredFiles = { "code.py", "boot.py", "plan.txt", "plan_engine.py", "live_light_guard.py", "guard_transition.py", "guard_calibration_protocol.py", "error_policy.py", "combined_guard_runtime.py", "desktop_steps.txt", "login_or_dc_steps.txt", "character_dashboard_steps.txt", "entering_game_loading_steps.txt", "game_steps.txt", "targeted_steps.txt", "resumable_steps.txt", "guard-transition.json", "guard-calibration.json", "SHA256SUMS.txt" };

    public static string[] List(string directory)
    {
        if (!Directory.Exists(directory)) throw new DirectoryNotFoundException(directory);
        return RequiredFiles.Where(name => File.Exists(Path.Combine(directory, name))).ToArray();
    }

    public static object ValidateBundle(string directory)
    {
        var missing = RequiredFiles.Where(name => !File.Exists(Path.Combine(directory, name))).ToArray();
        if (missing.Length > 0) throw new InvalidDataException("Missing required bundle file(s): " + string.Join(", ", missing));
        var manifest = JsonNode.Parse(File.ReadAllText(Path.Combine(directory, "guard-transition.json")))?.AsObject() ?? throw new InvalidDataException("guard-transition.json is not a JSON object.");
        var calibration = JsonNode.Parse(File.ReadAllText(Path.Combine(directory, "guard-calibration.json")))?.AsObject() ?? throw new InvalidDataException("guard-calibration.json is not a JSON object.");
        var manifestRevision = manifest["calibrationRevision"]?.GetValue<string>(); var calibrationRevision = calibration["revision"]?.GetValue<string>();
        if (string.IsNullOrWhiteSpace(manifestRevision) || manifestRevision != calibrationRevision) throw new InvalidDataException($"Manifest/calibration revision mismatch: {manifestRevision ?? "missing"} != {calibrationRevision ?? "missing"}.");
        var plan = File.ReadAllText(Path.Combine(directory, "plan.txt")); if (!plan.StartsWith("PLAN|2", StringComparison.Ordinal) || !plan.Contains("STATELOOP|", StringComparison.Ordinal)) throw new InvalidDataException("plan.txt is not a PLAN|2 STATELOOP entry plan.");
        var routes = RequiredFiles.Where(name => name.EndsWith("_steps.txt", StringComparison.Ordinal)).ToArray(); var badRoutes = routes.Where(name => !File.ReadAllText(Path.Combine(directory, name)).StartsWith("PLAN|2", StringComparison.Ordinal)).ToArray();
        if (badRoutes.Length > 0) throw new InvalidDataException("Invalid route plan(s): " + string.Join(", ", badRoutes));
        return new { valid = true, requiredFiles = RequiredFiles, calibrationRevision = manifestRevision, routeCount = routes.Length };
    }

    public static object ValidateHashes(string directory)
    {
        var hashPath = Path.Combine(directory, "SHA256SUMS.txt"); if (!File.Exists(hashPath)) throw new InvalidDataException("SHA256SUMS.txt is missing.");
        var expected = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var line in File.ReadAllLines(hashPath))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length != 2 || parts[0].Length != 64 || parts[0].Any(c => !Uri.IsHexDigit(c))) throw new InvalidDataException("Invalid SHA256SUMS.txt line: " + line);
            if (!expected.TryAdd(parts[1], parts[0].ToLowerInvariant())) throw new InvalidDataException("Duplicate hash entry: " + parts[1]);
        }
        var hashed = RequiredFiles.Where(name => !name.Equals("SHA256SUMS.txt", StringComparison.OrdinalIgnoreCase)).ToArray(); var missing = hashed.Where(name => !expected.ContainsKey(name) || !File.Exists(Path.Combine(directory, name))).ToArray();
        if (missing.Length > 0) throw new InvalidDataException("Missing hash entry/file: " + string.Join(", ", missing));
        var mismatches = new List<string>();
        foreach (var name in hashed) { var actual = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(directory, name)))).ToLowerInvariant(); if (!string.Equals(actual, expected[name], StringComparison.OrdinalIgnoreCase)) mismatches.Add(name); }
        if (mismatches.Count > 0) throw new InvalidDataException("SHA-256 mismatch: " + string.Join(", ", mismatches));
        return new { valid = true, hashedFiles = hashed.Length, manifest = hashPath };
    }

    public static void WaitForBundle(string directory, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout; while (DateTime.UtcNow < deadline) { if (RequiredFiles.All(name => File.Exists(Path.Combine(directory, name)))) return; Thread.Sleep(150); }
        throw new TimeoutException("Combined Guard export did not produce the complete staged bundle.");
    }
}
