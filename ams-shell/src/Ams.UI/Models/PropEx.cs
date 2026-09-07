using System.Text.Json;

namespace Ams.UI.Models;

/// <summary>
/// Tolerant readers for step parameter dictionaries. Values may be native types
/// (fresh from a dialog) or JsonElement (fresh from a .amsj file).
/// </summary>
public static class PropEx
{
    public static string GetString(IReadOnlyDictionary<string, object?> p, string key, string fallback = "")
        => p.TryGetValue(key, out var v) ? AsString(v) ?? fallback : fallback;

    public static int GetInt(IReadOnlyDictionary<string, object?> p, string key, int fallback = 0)
    {
        if (!p.TryGetValue(key, out var v)) return fallback;
        return v switch
        {
            int i => i,
            long l => (int)l,
            JsonElement { ValueKind: JsonValueKind.Number } je => je.GetInt32(),
            JsonElement { ValueKind: JsonValueKind.String } js when int.TryParse(js.GetString(), out var n) => n,
            string s when int.TryParse(s, out var n2) => n2,
            _ => fallback,
        };
    }

    public static bool GetBool(IReadOnlyDictionary<string, object?> p, string key, bool fallback = false)
    {
        if (!p.TryGetValue(key, out var v)) return fallback;
        return v switch
        {
            bool b => b,
            JsonElement { ValueKind: JsonValueKind.True } => true,
            JsonElement { ValueKind: JsonValueKind.False } => false,
            string s when bool.TryParse(s, out var b2) => b2,
            _ => fallback,
        };
    }

    private static string? AsString(object? v) => v switch
    {
        null => null,
        string s => s,
        JsonElement { ValueKind: JsonValueKind.String } je => je.GetString(),
        JsonElement je => je.ToString(),
        _ => v.ToString(),
    };
}
