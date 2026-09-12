using Ams.UI.Services;

namespace Ams.UI.ViewModels;

/// <summary>
/// v0.9.67 — Persian Play Options bindings for the portable automatic cycle.
/// Values live in ams-settings.json, never in the .amsj document.
/// </summary>
public partial class MainViewModel
{
    public int RestartMinMinutes
    {
        get => _settings.RestartMinMinutes;
        set
        {
            if (_settings.RestartMinMinutes == value) return;
            _settings.RestartMinMinutes = value;
            SaveAutoCycleOptions(nameof(RestartMinMinutes), nameof(RestartMaxMinutes));
        }
    }

    public int RestartMaxMinutes
    {
        get => _settings.RestartMaxMinutes;
        set
        {
            if (_settings.RestartMaxMinutes == value) return;
            _settings.RestartMaxMinutes = value;
            SaveAutoCycleOptions(nameof(RestartMinMinutes), nameof(RestartMaxMinutes));
        }
    }

    public bool AutoResumeEnabled
    {
        get => _settings.AutoResumeEnabled;
        set
        {
            if (_settings.AutoResumeEnabled == value) return;
            _settings.AutoResumeEnabled = value;
            _settings.Save();
            OnPropertyChanged();
            Log(value
                ? "چرخه‌ی خودکار: ادامه پس از Restart فعال شد"
                : "چرخه‌ی خودکار: ادامه پس از Restart غیرفعال شد");
        }
    }

    public int AutoResumeMinMinutes
    {
        get => _settings.AutoResumeMinMinutes;
        set
        {
            if (_settings.AutoResumeMinMinutes == value) return;
            _settings.AutoResumeMinMinutes = value;
            SaveAutoCycleOptions(nameof(AutoResumeMinMinutes), nameof(AutoResumeMaxMinutes));
        }
    }

    public int AutoResumeMaxMinutes
    {
        get => _settings.AutoResumeMaxMinutes;
        set
        {
            if (_settings.AutoResumeMaxMinutes == value) return;
            _settings.AutoResumeMaxMinutes = value;
            SaveAutoCycleOptions(nameof(AutoResumeMinMinutes), nameof(AutoResumeMaxMinutes));
        }
    }

    public bool PostRestartLaunchEnabled
    {
        get => _settings.PostRestartLaunchEnabled;
        set
        {
            if (_settings.PostRestartLaunchEnabled == value) return;
            _settings.PostRestartLaunchEnabled = value;
            _settings.Save();
            OnPropertyChanged();
            Log(value
                ? $"Restart Launch فعال شد — Win+{_settings.PostRestartTaskbarSlot}"
                : "Restart Launch غیرفعال شد");
        }
    }

    public int PostRestartTaskbarSlot
    {
        get => _settings.PostRestartTaskbarSlot;
        set
        {
            if (_settings.PostRestartTaskbarSlot == value) return;
            _settings.PostRestartTaskbarSlot = value;
            SaveAutoCycleOptions(nameof(PostRestartTaskbarSlot));
        }
    }

    public int PostRestartLaunchBeforeMinSeconds
    {
        get => _settings.PostRestartLaunchBeforeMinSeconds;
        set
        {
            if (_settings.PostRestartLaunchBeforeMinSeconds == value) return;
            _settings.PostRestartLaunchBeforeMinSeconds = value;
            SaveAutoCycleOptions(nameof(PostRestartLaunchBeforeMinSeconds),
                nameof(PostRestartLaunchBeforeMaxSeconds));
        }
    }

    public int PostRestartLaunchBeforeMaxSeconds
    {
        get => _settings.PostRestartLaunchBeforeMaxSeconds;
        set
        {
            if (_settings.PostRestartLaunchBeforeMaxSeconds == value) return;
            _settings.PostRestartLaunchBeforeMaxSeconds = value;
            SaveAutoCycleOptions(nameof(PostRestartLaunchBeforeMinSeconds),
                nameof(PostRestartLaunchBeforeMaxSeconds));
        }
    }

    public int PostRestartLaunchAfterMinSeconds
    {
        get => _settings.PostRestartLaunchAfterMinSeconds;
        set
        {
            if (_settings.PostRestartLaunchAfterMinSeconds == value) return;
            _settings.PostRestartLaunchAfterMinSeconds = value;
            SaveAutoCycleOptions(nameof(PostRestartLaunchAfterMinSeconds),
                nameof(PostRestartLaunchAfterMaxSeconds));
        }
    }

    public int PostRestartLaunchAfterMaxSeconds
    {
        get => _settings.PostRestartLaunchAfterMaxSeconds;
        set
        {
            if (_settings.PostRestartLaunchAfterMaxSeconds == value) return;
            _settings.PostRestartLaunchAfterMaxSeconds = value;
            SaveAutoCycleOptions(nameof(PostRestartLaunchAfterMinSeconds),
                nameof(PostRestartLaunchAfterMaxSeconds));
        }
    }

    /// <summary>The portable buzzer pin is intentionally not editable.</summary>
    public string PortableBuzzerPinText => AppSettings.PortableBuzzerPin + " (ثابت)";

    /// <summary>Short Persian explanation displayed below the cycle controls.</summary>
    public string AutoCycleHelpText =>
        "زمان از لحظه‌ی Start و بر اساس ساعت واقعی حساب می‌شود؛ مکث آن را تمدید نمی‌کند. " +
        "شروع خودکار فقط بعد از Restart طبیعی همین چرخه فعال است. خروجی بازر فقط GP6 است.";

    private void SaveAutoCycleOptions(params string[] properties)
    {
        _settings.NormalizeAutoCycleSettings();
        _settings.Save();
        foreach (var property in properties) OnPropertyChanged(property);
        Log($"چرخه‌ی خودکار ذخیره شد — Restart {_settings.RestartMinMinutes}–{_settings.RestartMaxMinutes} دقیقه، " +
            $"Resume {_settings.AutoResumeMinMinutes}–{_settings.AutoResumeMaxMinutes} دقیقه، " +
            $"Restart Launch Win+{_settings.PostRestartTaskbarSlot}، بازر {AppSettings.PortableBuzzerPin}");
    }
}
