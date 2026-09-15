using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private readonly List<double> _lightCalibrationSamples = new();
    private DateTimeOffset? _lightCalibrationStartedAt;
    private LightStateProfile? _selectedLightCalibrationProfile;
    private int _selectedLightCalibrationDurationSeconds = 5;
    private bool _isLightCalibrationRunning;
    private string _lightCalibrationStatus = "یک پروفایل و مدت نمونه‌برداری را انتخاب کنید.";
    private LightCalibrationSuggestion? _pendingLightCalibrationSuggestion;

    public IReadOnlyList<int> LightCalibrationDurationsSeconds { get; } = new[] { 3, 5, 10, 20 };

    public LightStateProfile? SelectedLightCalibrationProfile
    {
        get => _selectedLightCalibrationProfile;
        set => SetProperty(ref _selectedLightCalibrationProfile, value);
    }

    public int SelectedLightCalibrationDurationSeconds
    {
        get => _selectedLightCalibrationDurationSeconds;
        set => SetProperty(ref _selectedLightCalibrationDurationSeconds, Math.Clamp(value, 3, 20));
    }

    public bool IsLightCalibrationRunning
    {
        get => _isLightCalibrationRunning;
        private set => SetProperty(ref _isLightCalibrationRunning, value);
    }

    public string LightCalibrationStatus
    {
        get => _lightCalibrationStatus;
        private set => SetProperty(ref _lightCalibrationStatus, value);
    }

    public string LightCalibrationSuggestionDisplay => _pendingLightCalibrationSuggestion is null
        ? "پیشنهادی آماده نیست."
        : $"مرکز {_pendingLightCalibrationSuggestion.CenterLux:0.0} · تلورانس ±{_pendingLightCalibrationSuggestion.ToleranceLux:0.0} Lux · "
          + $"کمینه {_pendingLightCalibrationSuggestion.MinimumLux:0.0} · بیشینه {_pendingLightCalibrationSuggestion.MaximumLux:0.0} · "
          + $"{_pendingLightCalibrationSuggestion.SampleCount} نمونه";

    public bool StartLightProfileCalibration()
    {
        if (!IsLightWatchRunning || CurrentLux is null)
        {
            LightCalibrationStatus = "ابتدا پایش زنده را شروع کنید و منتظر یک نمونه معتبر بمانید.";
            return false;
        }
        if (SelectedLightCalibrationProfile is null)
        {
            LightCalibrationStatus = "ابتدا پروفایل مقصد را انتخاب کنید.";
            return false;
        }

        _lightCalibrationSamples.Clear();
        _pendingLightCalibrationSuggestion = null;
        _lightCalibrationStartedAt = DateTimeOffset.UtcNow;
        IsLightCalibrationRunning = true;
        OnPropertyChanged(nameof(LightCalibrationSuggestionDisplay));
        LightCalibrationStatus = $"نمونه‌برداری {SelectedLightCalibrationDurationSeconds} ثانیه‌ای برای «{SelectedLightCalibrationProfile.Name}» شروع شد.";
        return true;
    }

    public void CaptureLightCalibrationSample()
    {
        if (!IsLightCalibrationRunning || _lightCalibrationStartedAt is not DateTimeOffset started) return;
        if (CurrentLux is not double lux || !LightFreshnessText.StartsWith("به‌روز", StringComparison.Ordinal)) return;
        _lightCalibrationSamples.Add(lux);
        var elapsed = DateTimeOffset.UtcNow - started;
        LightCalibrationStatus = $"در حال نمونه‌برداری · {_lightCalibrationSamples.Count} نمونه · {Math.Min(elapsed.TotalSeconds, SelectedLightCalibrationDurationSeconds):0.0}/{SelectedLightCalibrationDurationSeconds} ثانیه";
        if (elapsed < TimeSpan.FromSeconds(SelectedLightCalibrationDurationSeconds)) return;

        IsLightCalibrationRunning = false;
        _lightCalibrationStartedAt = null;
        _pendingLightCalibrationSuggestion = LightCalibrationSuggester.Suggest(_lightCalibrationSamples);
        OnPropertyChanged(nameof(LightCalibrationSuggestionDisplay));
        LightCalibrationStatus = "پیشنهاد آماده است؛ هنوز هیچ پروفایلی تغییر نکرده است.";
    }

    public void CancelLightProfileCalibration()
    {
        IsLightCalibrationRunning = false;
        _lightCalibrationStartedAt = null;
        _lightCalibrationSamples.Clear();
        LightCalibrationStatus = "نمونه‌برداری لغو شد و هیچ مقداری تغییر نکرد.";
    }

    public bool ApplyPendingLightCalibrationSuggestion()
    {
        if (_pendingLightCalibrationSuggestion is null || SelectedLightCalibrationProfile is null)
        {
            LightCalibrationStatus = "پیشنهاد معتبری برای اعمال وجود ندارد.";
            return false;
        }
        SelectedLightCalibrationProfile.LuxCenter = _pendingLightCalibrationSuggestion.CenterLux;
        SelectedLightCalibrationProfile.LuxTolerance = _pendingLightCalibrationSuggestion.ToleranceLux;
        RefreshLightProfileWarnings();
        LightCalibrationStatus = "پیشنهاد روی فرم اعمال شد؛ برای ماندگارشدن، «ذخیره پروفایل‌ها» را بزنید.";
        return true;
    }
}
