using System.Globalization;

using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Strict, backward-compatible parser for Pico LUX? replies.</summary>
public static class LightTelemetryParser
{
    public static LightTelemetrySample Parse(string reply, DateTimeOffset? receivedAt = null)
    {
        ArgumentNullException.ThrowIfNull(reply);
        var raw = reply.Trim();
        var at = receivedAt ?? DateTimeOffset.UtcNow;

        var errorStatus = raw switch
        {
            "ERR|NOSENSOR|LUX" => LightTelemetryStatus.NoSensor,
            "ERR|I2C|LUX" => LightTelemetryStatus.I2cError,
            "ERR|BUSY|LUX" => LightTelemetryStatus.Busy,
            _ => (LightTelemetryStatus?)null,
        };
        if (errorStatus.HasValue)
            return new(errorStatus.Value, null, null, null, at, raw);

        var parts = raw.Split('|', StringSplitOptions.None);
        if (parts.Length < 4 || parts.Length > 6 || parts[0] != "OK" || parts[1] != "LUX")
            throw new LightTelemetryProtocolException(raw, "Expected an OK|LUX response.");

        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var i = 2; i < parts.Length; i++)
        {
            var separator = parts[i].IndexOf('=');
            if (separator <= 0 || separator == parts[i].Length - 1)
                throw new LightTelemetryProtocolException(raw, "Telemetry field is malformed.");
            if (!fields.TryAdd(parts[i][..separator], parts[i][(separator + 1)..]))
                throw new LightTelemetryProtocolException(raw, "Telemetry field is duplicated.");
        }

        // Combined Guard emits the compact shape:
        // OK|LUX|lux=10.8|sensor=ok
        // Older telemetry firmware may additionally include seq and mode. Both shapes are valid;
        // required values stay strict and optional values are validated when present.
        if (fields.Keys.Any(k => k is not ("seq" or "lux" or "mode" or "sensor"))
            || !fields.TryGetValue("lux", out var luxText)
            || !double.TryParse(luxText, NumberStyles.Float, CultureInfo.InvariantCulture, out var lux)
            || !double.IsFinite(lux) || lux < 0
            || !fields.TryGetValue("sensor", out var sensor) || sensor != "ok")
            throw new LightTelemetryProtocolException(raw, "Telemetry fields are invalid.");

        uint? sequence = null;
        if (fields.TryGetValue("seq", out var seqText))
        {
            if (!uint.TryParse(seqText, NumberStyles.None, CultureInfo.InvariantCulture, out var parsedSequence))
                throw new LightTelemetryProtocolException(raw, "Telemetry sequence is invalid.");
            sequence = parsedSequence;
        }

        string? mode = null;
        if (fields.TryGetValue("mode", out var modeText))
        {
            if (modeText is not ("hires" or "lowres"))
                throw new LightTelemetryProtocolException(raw, "Telemetry mode is invalid.");
            mode = modeText;
        }

        return new(LightTelemetryStatus.Ok, sequence, lux, mode, at, raw);
    }
}

public sealed class LightTelemetryProtocolException : FormatException
{
    public LightTelemetryProtocolException(string rawReply, string message)
        : base($"{message} Reply: {rawReply}") => RawReply = rawReply;

    public string RawReply { get; }
}
