using System.Globalization;

namespace Ams.UI.Services;

public sealed record LightGuardCalibrationResult(
    string ProfileId,
    double Center,
    double Spread,
    double Tolerance,
    int SampleCount,
    int StableDurationMs);

public sealed record LightGuardIdentity(
    string Version,
    string Role,
    bool HidOff,
    bool UartOff,
    bool ActuatorOff,
    int ProfileCount);

public sealed record LightGuardStateEvent(
    string ProfileId,
    double Lux,
    string Revision);

/// <summary>
/// Pure, UI-independent Phase 7 calibration math and line protocol.
/// It has no bridge, HID, execution or actuator dependency.
/// </summary>
public static class LightGuardCalibrationProtocol
{
    public static IReadOnlyList<string> ProfileIds { get; } = new[]
    {
        "desktop",
        "login-or-dc",
        "character-dashboard",
        "entering-game-loading",
        "game",
        "targeted",
    };

    public static LightGuardCalibrationResult? Compute(
        string profileId,
        IEnumerable<double> samples,
        int stableDurationMs = 750,
        double maximumSpread = 5.0)
    {
        if (!ProfileIds.Contains(profileId, StringComparer.Ordinal))
            throw new ArgumentException("Unknown Guard calibration profile.", nameof(profileId));
        if (stableDurationMs < 0) throw new ArgumentOutOfRangeException(nameof(stableDurationMs));
        if (maximumSpread < 0) throw new ArgumentOutOfRangeException(nameof(maximumSpread));

        var values = samples
            .Where(double.IsFinite)
            .Where(x => x >= 0)
            .ToArray();
        if (values.Length < 5) return null;

        Array.Sort(values);
        var center = values[values.Length / 2];
        var spread = values[^1] - values[0];
        if (spread > maximumSpread) return null;

        return new LightGuardCalibrationResult(
            profileId,
            center,
            spread,
            Math.Max(2.0, spread * 1.5),
            values.Length,
            stableDurationMs);
    }

    public static string BuildCalSet(
        string revision,
        LightGuardCalibrationResult result)
    {
        ArgumentNullException.ThrowIfNull(revision);
        ArgumentNullException.ThrowIfNull(result);
        EnsureToken(revision, nameof(revision));
        EnsureToken(result.ProfileId, nameof(result.ProfileId));
        return string.Join("|",
            "CALSET",
            revision,
            result.ProfileId,
            result.Center.ToString("0.###", CultureInfo.InvariantCulture),
            result.Tolerance.ToString("0.###", CultureInfo.InvariantCulture),
            result.StableDurationMs.ToString(CultureInfo.InvariantCulture));
    }

    public static bool TryParseIdentity(string? line, out LightGuardIdentity? identity)
    {
        identity = null;
        if (string.IsNullOrWhiteSpace(line)) return false;
        var fields = line.Split('|');
        if (fields.Length < 2 || fields[0] != "OK" || fields[1] != "PONG") return false;

        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var field in fields.Skip(2))
        {
            var separator = field.IndexOf('=');
            if (separator <= 0) continue;
            values[field[..separator]] = field[(separator + 1)..];
        }

        if (!values.TryGetValue("role", out var role)
            || !values.TryGetValue("hid", out var hid)
            || !values.TryGetValue("uart", out var uart)
            || !values.TryGetValue("profiles", out var count)
            || !int.TryParse(count, NumberStyles.Integer, CultureInfo.InvariantCulture, out var profileCount)) return false;

        var legacy = string.Equals(role, "light-guard", StringComparison.Ordinal)
            && string.Equals(hid, "off", StringComparison.Ordinal)
            && string.Equals(uart, "off", StringComparison.Ordinal)
            && values.TryGetValue("actuator", out var actuator)
            && string.Equals(actuator, "off", StringComparison.Ordinal)
            && fields[2].StartsWith("pico-light-guard ", StringComparison.Ordinal);
        var combinedBrain = string.Equals(role, "brain", StringComparison.Ordinal)
            && string.Equals(hid, "on", StringComparison.Ordinal)
            && string.Equals(uart, "on", StringComparison.Ordinal)
            && fields[2].StartsWith("combined-pico-guard-executor", StringComparison.Ordinal);
        if (!legacy && !combinedBrain) return false;

        identity = new LightGuardIdentity(
            legacy ? fields[2]["pico-light-guard ".Length..] : fields[2],
            role,
            HidOff: legacy,
            UartOff: legacy,
            ActuatorOff: legacy,
            profileCount);
        return true;
    }

    public static bool TryParseStateEvent(string? line, out LightGuardStateEvent? state)
    {
        state = null;
        if (string.IsNullOrWhiteSpace(line)) return false;
        var fields = line.Split('|');
        if (fields.Length < 4 || fields[0] != "EVT" || fields[1] != "GUARD") return false;

        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var field in fields.Skip(2))
        {
            var separator = field.IndexOf('=');
            if (separator <= 0) continue;
            values[field[..separator]] = field[(separator + 1)..];
        }

        if (!values.TryGetValue("state", out var profileId)
            || !ProfileIds.Contains(profileId, StringComparer.Ordinal)) return false;
        if (!values.TryGetValue("lux", out var luxText)
            || !double.TryParse(luxText, NumberStyles.Float, CultureInfo.InvariantCulture, out var lux)
            || !double.IsFinite(lux) || lux < 0) return false;
        if (!values.TryGetValue("revision", out var revision)) return false;

        state = new LightGuardStateEvent(profileId, lux, revision);
        return true;
    }

    private static void EnsureToken(string value, string name)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Contains('|') || value.Contains('\r') || value.Contains('\n'))
            throw new ArgumentException("Protocol token is empty or contains a delimiter.", name);
    }
}
