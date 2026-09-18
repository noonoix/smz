using System.IO;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Persists editable light profiles outside .amsj plans. Missing or corrupt data falls back safely.</summary>
public static class LightStateProfileStore
{
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };
    private static string DefaultPath => Path.Combine(AppContext.BaseDirectory, "light-state-profiles.json");

    public static List<LightStateProfile> Load(string? path = null)
    {
        path ??= DefaultPath;
        try
        {
            if (!File.Exists(path)) return LightStateDefaults.CreateInitialProfiles();
            var profiles = JsonSerializer.Deserialize<List<LightStateProfile>>(File.ReadAllText(path), Options);
            return Normalize(profiles);
        }
        catch
        {
            return LightStateDefaults.CreateInitialProfiles();
        }
    }

    public static void Save(IEnumerable<LightStateProfile> profiles, string? path = null)
    {
        path ??= DefaultPath;
        var normalized = Normalize(profiles);
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrWhiteSpace(directory)) Directory.CreateDirectory(directory);
        var temporary = path + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(normalized, Options));
        File.Move(temporary, path, overwrite: true);
    }

    /// <summary>
    /// Normalizes old profile files without discarding valid user values. Older builds
    /// could persist only five rows; missing canonical Guard profiles are now backfilled
    /// from defaults, including the combined Login / DC profile.
    /// </summary>
    public static List<LightStateProfile> Normalize(IEnumerable<LightStateProfile>? profiles)
    {
        var defaults = LightStateDefaults.CreateInitialProfiles();
        if (profiles is null) return defaults;

        var valid = profiles
            .Where(p => p is not null && p.IsValid)
            .GroupBy(p => p.Id, StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.First(), StringComparer.Ordinal);

        // Canonical order is part of the UI/protocol contract. Existing values win;
        // a missing row is inserted with the safe default rather than being omitted.
        var normalized = defaults
            .Select(d => valid.TryGetValue(d.Id, out var existing) ? existing : d)
            .ToList();

        // Preserve any future/unknown valid rows after the canonical six instead of
        // silently deleting user data.
        var known = defaults.Select(d => d.Id).ToHashSet(StringComparer.Ordinal);
        normalized.AddRange(valid.Values.Where(p => !known.Contains(p.Id)));
        return normalized;
    }
}
