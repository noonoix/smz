using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

public sealed record LightGuardCalibrationEvent(
    string Mode,
    int? Stage,
    string? ProfileId,
    double? Center,
    double? Spread,
    double? Tolerance,
    string? Revision,
    string? Reason,
    int? Count);

public sealed record LightGuardDeviceCalibration(string Revision, int Count);

public sealed record LightGuardDeviceStatus(
    string Revision,
    int Count,
    IReadOnlyDictionary<string, double> Centers);

/// <summary>
/// Phase 7 app-side adapter. It owns only the Guard protocol, revision identity and
/// observation/calibration display data; it has no RunEngine, HID, keyboard, mouse or actuator path.
/// </summary>
public static class LightGuardAppAdapter
{
    public static string ComputeRevision(IEnumerable<LightStateProfile> profiles)
    {
        ArgumentNullException.ThrowIfNull(profiles);
        var byId = profiles.ToDictionary(x => x.Id, StringComparer.Ordinal);
        if (byId.Count != LightGuardCalibrationProtocol.ProfileIds.Count
            || LightGuardCalibrationProtocol.ProfileIds.Any(id => !byId.ContainsKey(id)))
            throw new ArgumentException("Exactly the six canonical Guard profiles are required.", nameof(profiles));
        if (LightGuardCalibrationProtocol.ProfileIds.Any(id => !byId[id].IsValid))
            throw new ArgumentException("Guard profiles must be valid before synchronization.", nameof(profiles));

        var canonical = string.Join("\n", LightGuardCalibrationProtocol.ProfileIds.Select(id =>
        {
            var profile = byId[id];
            return string.Join("|", id,
                profile.LuxCenter.ToString("0.###", CultureInfo.InvariantCulture),
                profile.LuxTolerance.ToString("0.###", CultureInfo.InvariantCulture),
                profile.StableDurationMs.ToString(CultureInfo.InvariantCulture));
        }));
        var digest = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonical))).ToLowerInvariant();
        return "guard-" + digest[..16];
    }

    public static string BuildCalSet(string revision, LightStateProfile profile)
    {
        ArgumentNullException.ThrowIfNull(profile);
        if (!profile.IsValid) throw new ArgumentException("Profile is invalid.", nameof(profile));
        return LightGuardCalibrationProtocol.BuildCalSet(revision,
            new LightGuardCalibrationResult(profile.Id, profile.LuxCenter, 0,
                profile.LuxTolerance, 0, profile.StableDurationMs));
    }

    public static bool TryParseCalGet(string? line, out LightGuardDeviceCalibration? result)
    {
        result = null;
        var fields = SplitFields(line, "OK", "CALGET");
        if (fields is null) return false;
        if (!TryValue(fields, "revision", out var revision)
            || !TryValue(fields, "count", out var countText)
            || !int.TryParse(countText, NumberStyles.Integer, CultureInfo.InvariantCulture, out var count)
            || count < 0)
            return false;
        result = new LightGuardDeviceCalibration(revision, count);
        return true;
    }

    public static bool TryParseCalStatus(string? line, out LightGuardDeviceStatus? result)
    {
        result = null;
        var fields = SplitFields(line, "OK", "CALSTATUS");
        if (fields is null
            || !TryValue(fields, "revision", out var revision)
            || !TryValue(fields, "count", out var countText)
            || !int.TryParse(countText, NumberStyles.Integer, CultureInfo.InvariantCulture, out var count)
            || count < 0
            || !TryValue(fields, "profiles", out var profilesText)) return false;

        var centers = new Dictionary<string, double>(StringComparer.Ordinal);
        foreach (var item in profilesText.Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            var at = item.IndexOf(':');
            if (at <= 0
                || !double.TryParse(item[(at + 1)..], NumberStyles.Float, CultureInfo.InvariantCulture, out var center)
                || !double.IsFinite(center) || center < 0) return false;
            centers[item[..at]] = center;
        }
        result = new LightGuardDeviceStatus(revision, count, centers);
        return true;
    }

    public static bool TryParseCalibrationEvent(string? line, out LightGuardCalibrationEvent? result)
    {
        result = null;
        var fields = SplitFields(line, "EVT", "CAL");
        if (fields is null || !TryValue(fields, "mode", out var mode)) return false;
        int? stage = TryInt(fields, "stage");
        double? center = TryDouble(fields, "center");
        double? spread = TryDouble(fields, "spread");
        double? tolerance = TryDouble(fields, "tolerance");
        int? count = TryInt(fields, "count");
        fields.TryGetValue("id", out var profileId);
        fields.TryGetValue("revision", out var revision);
        fields.TryGetValue("reason", out var reason);
        result = new LightGuardCalibrationEvent(mode, stage, profileId, center, spread, tolerance, revision, reason, count);
        return true;
    }

    /// <summary>PythonBoardBridge emits JSON lines; tests and fakes may provide the raw EVT line.</summary>
    public static bool TryExtractEventLine(string? bridgeLine, out string eventLine)
    {
        eventLine = string.Empty;
        if (string.IsNullOrWhiteSpace(bridgeLine)) return false;
        if (bridgeLine.StartsWith("EVT|", StringComparison.Ordinal))
        {
            eventLine = bridgeLine;
            return true;
        }
        try
        {
            using var doc = JsonDocument.Parse(bridgeLine);
            var root = doc.RootElement;
            if (!root.TryGetProperty("event", out var kind)
                || !string.Equals(kind.GetString(), "evt", StringComparison.Ordinal)
                || !root.TryGetProperty("line", out var line)) return false;
            var value = line.GetString();
            if (string.IsNullOrWhiteSpace(value) || !value.StartsWith("EVT|", StringComparison.Ordinal)) return false;
            eventLine = value;
            return true;
        }
        catch (JsonException) { return false; }
    }

    private static Dictionary<string, string>? SplitFields(string? line, string first, string second)
    {
        if (string.IsNullOrWhiteSpace(line)) return null;
        var parts = line.Split('|');
        if (parts.Length < 2 || parts[0] != first || parts[1] != second) return null;
        var fields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var part in parts.Skip(2))
        {
            var at = part.IndexOf('=');
            if (at > 0) fields[part[..at]] = part[(at + 1)..];
        }
        return fields;
    }

    private static bool TryValue(Dictionary<string, string> fields, string key, out string value)
        => fields.TryGetValue(key, out value!) && !string.IsNullOrWhiteSpace(value);

    private static int? TryInt(Dictionary<string, string> fields, string key)
        => fields.TryGetValue(key, out var value)
           && int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed : null;

    private static double? TryDouble(Dictionary<string, string> fields, string key)
        => fields.TryGetValue(key, out var value)
           && double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
           && double.IsFinite(parsed) ? parsed : null;
}
