using System.Text.Json;

namespace Ams.UI.Services;

/// <summary>Application-wide error routing policy. It is deliberately independent of the
/// active pipeline tab so Launch, Main, recovery and resume runs share one behaviour.</summary>
public sealed class ErrorPolicySettings
{
    public bool FatalAlarmEnabled { get; set; } = true;
    public string AlarmSource { get; set; } = "both"; // pico, pc, both
    public bool RepeatAlarm { get; set; } = true;
    public int AlarmDurationSeconds { get; set; } = 0; // 0 = until acknowledgement/Stop
    public string TimeoutPolicy { get; set; } = "stopWithAlarm"; // stopWithAlarm, stopQuiet, continue
    public int ErrorHistoryLimit { get; set; } = 20;
    public List<ErrorRecord> ErrorHistory { get; set; } = new();

    private static string FilePath => Path.Combine(AppContext.BaseDirectory, "ams-error-policy.json");

    public static ErrorPolicySettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
            {
                var value = JsonSerializer.Deserialize<ErrorPolicySettings>(File.ReadAllText(FilePath));
                if (value is not null) { value.Normalize(); return value; }
            }
        }
        catch { /* corrupt settings must never prevent the application from starting */ }
        return new ErrorPolicySettings();
    }

    public void Save()
    {
        Normalize();
        try
        {
            var tmp = FilePath + ".tmp";
            File.WriteAllText(tmp, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
            File.Move(tmp, FilePath, true);
        }
        catch { /* settings are best effort; execution must continue */ }
    }

    public void Record(string source, Exception error, string? tab = null)
    {
        Normalize();
        ErrorHistory.Add(new ErrorRecord(DateTimeOffset.Now, source, error.Message, tab));
        if (ErrorHistory.Count > ErrorHistoryLimit)
            ErrorHistory.RemoveRange(0, ErrorHistory.Count - ErrorHistoryLimit);
        Save();
    }

    public void Normalize()
    {
        AlarmSource = AlarmSource?.ToLowerInvariant() switch { "pico" or "pc" or "both" => AlarmSource.ToLowerInvariant(), _ => "both" };
        TimeoutPolicy = TimeoutPolicy?.ToLowerInvariant() switch { "stopquiet" or "stopquietly" => "stopQuiet", "continue" => "continue", _ => "stopWithAlarm" };
        ErrorHistoryLimit = Math.Clamp(ErrorHistoryLimit, 0, 100);
        AlarmDurationSeconds = Math.Clamp(AlarmDurationSeconds, 0, 3600);
        ErrorHistory ??= new();
        if (ErrorHistory.Count > ErrorHistoryLimit && ErrorHistoryLimit >= 0)
            ErrorHistory.RemoveRange(0, ErrorHistory.Count - ErrorHistoryLimit);
    }
}

public sealed record ErrorRecord(DateTimeOffset Time, string Source, string Message, string? Tab);
