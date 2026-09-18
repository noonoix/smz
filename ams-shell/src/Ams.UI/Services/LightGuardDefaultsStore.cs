using System.Text.Json;

namespace Ams.UI.Services;

public sealed record LightGuardDefaultSettings(double Tolerance, int StableDurationMs, double HysteresisLux);

public static class LightGuardDefaultsStore
{
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };
    private static string PathName => Path.Combine(AppContext.BaseDirectory, "light-guard-defaults.json");
    public static LightGuardDefaultSettings Load()
    {
        try
        {
            if (!File.Exists(PathName)) return new(2.0, 750, 1.0);
            return JsonSerializer.Deserialize<LightGuardDefaultSettings>(File.ReadAllText(PathName), Options)
                is { Tolerance: >= 0, StableDurationMs: >= 0, HysteresisLux: >= 0 } value
                ? value : new(2.0, 750, 1.0);
        }
        catch { return new(2.0, 750, 1.0); }
    }
    public static void Save(LightGuardDefaultSettings value)
    {
        if (!double.IsFinite(value.Tolerance) || value.Tolerance < 0
            || value.StableDurationMs < 0 || !double.IsFinite(value.HysteresisLux) || value.HysteresisLux < 0)
            throw new ArgumentOutOfRangeException(nameof(value));
        File.WriteAllText(PathName, JsonSerializer.Serialize(value, Options));
    }
}
