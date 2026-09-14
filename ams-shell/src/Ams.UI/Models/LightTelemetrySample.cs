namespace Ams.UI.Models;

/// <summary>Typed result of one read-only LUX? request.</summary>
public sealed record LightTelemetrySample(
    LightTelemetryStatus Status,
    uint? Sequence,
    double? Lux,
    string? Mode,
    DateTimeOffset ReceivedAt,
    string RawReply)
{
    public bool IsSuccess => Status == LightTelemetryStatus.Ok;
}

public enum LightTelemetryStatus
{
    Ok,
    NoSensor,
    I2cError,
    Busy,
}
