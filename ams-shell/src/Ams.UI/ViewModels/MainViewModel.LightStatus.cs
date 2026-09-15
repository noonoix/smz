using Ams.UI.Models;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private readonly Queue<(DateTimeOffset At, double Lux)> _lightHistory = new();
    private readonly Queue<double> _lightMedianWindow = new();
    private LightWatchService? _lightWatch;
    private IBoardBridge? _lightWatchBridge;
    private System.Windows.Threading.DispatcherTimer? _lightFreshnessTimer;
    private DateTimeOffset? _lastSuccessfulLightAt;
    private int _activeLightIntervalMs = LightWatchService.DefaultIntervalMs;
    private int _selectedLightWatchIntervalMs = LightWatchService.DefaultIntervalMs;
    private bool _isLightWatchRunning;
    private double? _currentLux;
    private string _lightSensorStatus = "بدون داده";
    private string _lightSensorMode = "—";
    private string _lastLightSampleText = "هنوز نمونه‌ای دریافت نشده";
    private string _lightFreshnessText = "بدون نمونه معتبر";
    private double? _lightMinimum;
    private double? _lightMaximum;
    private double? _lightAverage;
    private int _lightChartVersion;

    public IReadOnlyList<int> LightWatchIntervalsMs { get; } = new[] { 100, 250, 500, 1000 };

    public int SelectedLightWatchIntervalMs
    {
        get => _selectedLightWatchIntervalMs;
        set => SetProperty(ref _selectedLightWatchIntervalMs, value);
    }

    public bool IsLightWatchRunning
    {
        get => _isLightWatchRunning;
        private set
        {
            if (!SetProperty(ref _isLightWatchRunning, value)) return;
            OnPropertyChanged(nameof(LightWatchButtonText));
        }
    }

    public string LightWatchButtonText => IsLightWatchRunning ? "توقف پایش" : "شروع پایش";

    public double? CurrentLux
    {
        get => _currentLux;
        private set
        {
            if (!SetProperty(ref _currentLux, value)) return;
            OnPropertyChanged(nameof(CurrentLuxDisplay));
        }
    }
    public string CurrentLuxDisplay => CurrentLux is double value ? value.ToString("0.0") : "—";

    public string LightSensorStatus { get => _lightSensorStatus; private set => SetProperty(ref _lightSensorStatus, value); }
    public string LightSensorMode { get => _lightSensorMode; private set => SetProperty(ref _lightSensorMode, value); }
    public string LastLightSampleText { get => _lastLightSampleText; private set => SetProperty(ref _lastLightSampleText, value); }
    public string LightFreshnessText { get => _lightFreshnessText; private set => SetProperty(ref _lightFreshnessText, value); }

    public double? LightMinimum
    {
        get => _lightMinimum;
        private set { if (SetProperty(ref _lightMinimum, value)) OnPropertyChanged(nameof(LightMinimumDisplay)); }
    }
    public double? LightMaximum
    {
        get => _lightMaximum;
        private set { if (SetProperty(ref _lightMaximum, value)) OnPropertyChanged(nameof(LightMaximumDisplay)); }
    }
    public double? LightAverage
    {
        get => _lightAverage;
        private set
        {
            if (!SetProperty(ref _lightAverage, value)) return;
            OnPropertyChanged(nameof(LightAverageDisplay));
            OnPropertyChanged(nameof(LightSpreadDisplay));
        }
    }
    public string LightMinimumDisplay => LightMinimum is double value ? value.ToString("0.0") : "—";
    public string LightMaximumDisplay => LightMaximum is double value ? value.ToString("0.0") : "—";
    public string LightAverageDisplay => LightAverage is double value ? value.ToString("0.0") : "—";
    public string LightSpreadDisplay => LightMinimum is double lo && LightMaximum is double hi ? (hi - lo).ToString("0.0") : "—";
    public int LightChartVersion { get => _lightChartVersion; private set => SetProperty(ref _lightChartVersion, value); }

    [RelayCommand]
    private async Task ToggleLightWatch()
    {
        if (IsLightWatchRunning) await StopLightWatchAsync();
        else await StartLightWatchAsync();
    }

    private async Task StartLightWatchAsync()
    {
        if (_bridge is null || Connection != ConnectionState.Connected || _bridge.State != BridgeState.Connected)
        {
            LightSensorStatus = "برد متصل نیست";
            Log("light watch: connect the Pico first");
            return;
        }

        await StopLightWatchAsync();
        _activeLightIntervalMs = SelectedLightWatchIntervalMs;
        var service = new LightWatchService(_bridge);
        service.SampleReceived += OnLightSampleReceived;
        service.WatchFaulted += OnLightWatchFaulted;
        _bridge.StateChanged += OnLightBridgeStateChanged;
        _lightWatch = service;
        _lightWatchBridge = _bridge;
        try
        {
            await service.StartAsync(TimeSpan.FromMilliseconds(_activeLightIntervalMs));
            IsLightWatchRunning = true;
            LightSensorStatus = "در انتظار اولین نمونه";
            EnsureLightFreshnessTimer();
            Log($"light watch started — interval {_activeLightIntervalMs} ms, read-only");
        }
        catch (Exception ex)
        {
            await StopLightWatchAsync();
            LightSensorStatus = "شروع پایش ناموفق";
            Log("light watch start failed: " + ex.Message);
        }
    }

    private async Task StopLightWatchAsync()
    {
        var service = _lightWatch;
        var bridge = _lightWatchBridge;
        _lightWatch = null;
        _lightWatchBridge = null;
        if (bridge is not null) bridge.StateChanged -= OnLightBridgeStateChanged;
        if (service is not null)
        {
            service.SampleReceived -= OnLightSampleReceived;
            service.WatchFaulted -= OnLightWatchFaulted;
            try { await service.DisposeAsync(); } catch (Exception ex) { Log("light watch stop: " + ex.Message); }
        }
        IsLightWatchRunning = false;
        UpdateLightFreshness();
    }

    private void OnLightBridgeStateChanged(object? sender, BridgeState state)
    {
        if (state == BridgeState.Connected) return;
        RunOnUi(async () =>
        {
            await StopLightWatchAsync();
            LightSensorStatus = "اتصال Pico قطع شد";
            Log("light watch stopped — board disconnected");
        });
    }

    private void OnLightWatchFaulted(Exception ex) => RunOnUi(() =>
    {
        LightSensorStatus = "خطای دریافت داده";
        Log("light watch: " + ex.Message);
    });

    private void OnLightSampleReceived(LightTelemetrySample sample) => RunOnUi(() => ApplyLightSample(sample));

    private void ApplyLightSample(LightTelemetrySample sample)
    {
        LastLightSampleText = sample.ReceivedAt.ToLocalTime().ToString("HH:mm:ss.fff");
        switch (sample.Status)
        {
            case LightTelemetryStatus.Ok when sample.Lux is double lux:
                LightSensorStatus = "سنسور سالم";
                LightSensorMode = sample.Mode ?? "—";
                _lastSuccessfulLightAt = sample.ReceivedAt;
                _lightMedianWindow.Enqueue(lux);
                while (_lightMedianWindow.Count > 5) _lightMedianWindow.Dequeue();
                CurrentLux = Median(_lightMedianWindow);
                _lightHistory.Enqueue((sample.ReceivedAt, lux));
                TrimLightHistory(sample.ReceivedAt);
                RefreshLightStatistics();
                LightChartVersion++;
                break;
            case LightTelemetryStatus.NoSensor:
                LightSensorStatus = "سنسور BH1750 پیدا نشد";
                LightSensorMode = "—";
                break;
            case LightTelemetryStatus.I2cError:
                LightSensorStatus = "خطای I2C سنسور";
                break;
            case LightTelemetryStatus.Busy:
                LightSensorStatus = "برد مشغول اجرای فرمان است";
                break;
        }
        UpdateLightFreshness();
    }

    private void EnsureLightFreshnessTimer()
    {
        _lightFreshnessTimer ??= new System.Windows.Threading.DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(500),
        };
        _lightFreshnessTimer.Tick -= OnLightFreshnessTick;
        _lightFreshnessTimer.Tick += OnLightFreshnessTick;
        _lightFreshnessTimer.Start();
    }

    private void OnLightFreshnessTick(object? sender, EventArgs e)
    {
        if (_lightWatch is { IsRunning: false } && IsLightWatchRunning)
        {
            IsLightWatchRunning = false;
            LightSensorStatus = Connection == ConnectionState.Connected ? "پایش متوقف شد" : "اتصال Pico قطع شد";
        }
        UpdateLightFreshness();
    }

    private void UpdateLightFreshness()
    {
        if (_lastSuccessfulLightAt is not DateTimeOffset last)
        {
            LightFreshnessText = "بدون نمونه معتبر";
            return;
        }
        var age = DateTimeOffset.UtcNow - last.ToUniversalTime();
        var threshold = LightWatchService.GetStaleThreshold(TimeSpan.FromMilliseconds(_activeLightIntervalMs));
        LightFreshnessText = age > threshold
            ? $"داده قدیمی · {age.TotalSeconds:0.0} ثانیه"
            : $"به‌روز · {age.TotalSeconds:0.0} ثانیه قبل";
    }

    private void TrimLightHistory(DateTimeOffset now)
    {
        var cutoff = now - TimeSpan.FromSeconds(60);
        while (_lightHistory.Count > 0 && (_lightHistory.Peek().At < cutoff || _lightHistory.Count > 600))
            _lightHistory.Dequeue();
    }

    private void RefreshLightStatistics()
    {
        if (_lightHistory.Count == 0)
        {
            LightMinimum = LightMaximum = LightAverage = null;
            return;
        }
        LightMinimum = _lightHistory.Min(x => x.Lux);
        LightMaximum = _lightHistory.Max(x => x.Lux);
        LightAverage = _lightHistory.Average(x => x.Lux);
        OnPropertyChanged(nameof(LightSpreadDisplay));
    }

    public IReadOnlyList<double> GetLightChartLuxSnapshot() => _lightHistory.Select(x => x.Lux).ToArray();

    private static double Median(IEnumerable<double> values)
    {
        var ordered = values.OrderBy(x => x).ToArray();
        if (ordered.Length == 0) return 0;
        var middle = ordered.Length / 2;
        return ordered.Length % 2 == 0 ? (ordered[middle - 1] + ordered[middle]) / 2 : ordered[middle];
    }

    private static void RunOnUi(Action action)
    {
        var dispatcher = System.Windows.Application.Current?.Dispatcher;
        if (dispatcher is not null && !dispatcher.CheckAccess()) dispatcher.BeginInvoke(action);
        else action();
    }

    private static void RunOnUi(Func<Task> action)
    {
        var dispatcher = System.Windows.Application.Current?.Dispatcher;
        if (dispatcher is not null && !dispatcher.CheckAccess()) dispatcher.BeginInvoke(action);
        else _ = action();
    }
}
