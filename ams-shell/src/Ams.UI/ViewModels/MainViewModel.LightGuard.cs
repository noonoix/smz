using System.Collections.ObjectModel;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private bool _lightGuardLineHooked;
    private string _lightGuardIdentityDisplay = "شناسایی نشده — فقط Pico Guard مجاز است";
    private string _lightGuardRevisionDisplay = "نسخهٔ کالیبراسیون: —";
    private string _lightGuardRevisionComparison = "همگام‌سازی هنوز بررسی نشده است.";
    private string _lightGuardCalibrationStatus = "برای کالیبراسیون فیزیکی، GP4 را سه ثانیه نگه دارید.";
    private string _lightGuardObservationStatus = "پایش Guard خاموش است.";
    private string _lightGuardStateDisplay = "نامشخص";
    private bool _lightGuardIdentityValid;
    private bool _lightGuardCalibrationSynchronized;
    private bool _lightGuardObservationEnabled;

    public ObservableCollection<string> LightGuardProfileDisplays { get; } = new();
    public ObservableCollection<string> LightGuardComparisonDisplays { get; } = new();
    private string _lightGuardComparisonStatus = "مقایسه با Pico هنوز انجام نشده است.";

    public string LightGuardComparisonStatus { get => _lightGuardComparisonStatus; private set => SetProperty(ref _lightGuardComparisonStatus, value); }

    public string LightGuardIdentityDisplay { get => _lightGuardIdentityDisplay; private set => SetProperty(ref _lightGuardIdentityDisplay, value); }
    public string LightGuardRevisionDisplay { get => _lightGuardRevisionDisplay; private set => SetProperty(ref _lightGuardRevisionDisplay, value); }
    public string LightGuardRevisionComparison { get => _lightGuardRevisionComparison; private set => SetProperty(ref _lightGuardRevisionComparison, value); }
    public string LightGuardCalibrationStatus { get => _lightGuardCalibrationStatus; private set => SetProperty(ref _lightGuardCalibrationStatus, value); }
    public string LightGuardObservationStatus { get => _lightGuardObservationStatus; private set => SetProperty(ref _lightGuardObservationStatus, value); }
    public string LightGuardStateDisplay { get => _lightGuardStateDisplay; private set => SetProperty(ref _lightGuardStateDisplay, value); }
    public bool LightGuardIdentityValid { get => _lightGuardIdentityValid; private set => SetProperty(ref _lightGuardIdentityValid, value); }
    public bool LightGuardCalibrationSynchronized { get => _lightGuardCalibrationSynchronized; private set => SetProperty(ref _lightGuardCalibrationSynchronized, value); }
    public bool LightGuardObservationEnabled { get => _lightGuardObservationEnabled; private set => SetProperty(ref _lightGuardObservationEnabled, value); }

    public void InitializeLightGuardAdapter()
    {
        if (!_lightGuardLineHooked && _bridge is not null)
        {
            _bridge.LineReceived += OnLightGuardBridgeLine;
            _lightGuardLineHooked = true;
        }
        RefreshLightGuardProfileDisplays();
        OnPropertyChanged(nameof(LightGuardIdentityValid));
        OnPropertyChanged(nameof(LightGuardCalibrationSynchronized));
    }

    public async Task RefreshLightGuardIdentityAsync()
    {
        InitializeLightGuardAdapter();
        LightGuardCalibrationSynchronized = false;
        if (_bridge is null || Connection != ConnectionState.Connected)
        {
            LightGuardIdentityValid = false;
            LightGuardIdentityDisplay = "برد متصل نیست — PING Guard انجام نشد";
            LightGuardRevisionComparison = "نامشخص: ابتدا Guard را با PING شناسایی کنید.";
            return;
        }
        try
        {
            var pong = await _bridge.SendAsync("PING");
            if (!LightGuardCalibrationProtocol.TryParseIdentity(pong, out var identity) || identity is null)
            {
                LightGuardIdentityValid = false;
                LightGuardIdentityDisplay = "هویت نامعتبر — این پورت Guard شناخته‌شده نیست";
                LightGuardRevisionComparison = "همگام‌سازی مسدود شد: هویت Guard معتبر نیست.";
                Log("phase7 Guard: identity mismatch; CALSET blocked");
                return;
            }
            LightGuardIdentityValid = identity.ProfileCount == 6;
            LightGuardIdentityDisplay = LightGuardIdentityValid
                ? identity.Role == "brain"
                    ? $"Combined Guard معتبر · {identity.Version} · نقش brain · ۶ پروفایل · کانال سخت‌افزار فعال"
                    : $"Guard معتبر · {identity.Version} · ۶ پروفایل · HID/UART/actuator خاموش"
                : $"Guard نامعتبر · profiles={identity.ProfileCount} (باید 6 باشد)";
            if (!LightGuardIdentityValid) return;

            var calget = await _bridge.SendAsync("CALGET");
            if (!LightGuardAppAdapter.TryParseCalGet(calget, out var device) || device is null)
            {
                LightGuardRevisionDisplay = "نسخهٔ کالیبراسیون: پاسخ CALGET نامعتبر";
                LightGuardRevisionComparison = "همگام‌سازی مسدود شد: CALGET نامعتبر است.";
                return;
            }
            var appRevision = LightGuardAppAdapter.ComputeRevision(LightStateProfiles);
            var revisionMatches = device.Count == 6 && device.Revision == appRevision;
            LightGuardRevisionDisplay = $"نسخهٔ Pico: {device.Revision:-} · رکوردها: {device.Count}/6 · نسخهٔ برنامه: {appRevision}";
            LightGuardRevisionComparison = revisionMatches
                ? "revision یکسان است؛ برای اعتماد این جلسه باید هر شش CALSET دوباره تأیید شوند."
                : "عدم تطابق یا کالیبراسیون ناقص؛ قبل از استفاده Sync را اجرا کنید.";
            LightGuardCalibrationStatus = revisionMatches
                ? "هویت معتبر است، اما Guard تا تأیید شش CALSET در این جلسه روشن نمی‌شود."
                : "کالیبراسیون Pico با منبع حقیقت برنامه همگام نیست.";
            Log($"phase7 Guard: {LightGuardIdentityDisplay}; CALGET revision={device.Revision}, count={device.Count}");
        }
        catch (Exception ex)
        {
            LightGuardIdentityValid = false;
            LightGuardIdentityDisplay = "خطا در شناسایی Guard — fail closed";
            LightGuardRevisionComparison = "همگام‌سازی انجام نشد: " + ex.Message;
            Log("phase7 Guard identity failed: " + ex.Message);
        }
    }

    public async Task PullLightGuardCalibrationAsync()
    {
        InitializeLightGuardAdapter();
        if (_bridge is null || Connection != ConnectionState.Connected)
        {
            LightGuardCalibrationStatus = "دریافت مسدود شد: برد متصل نیست.";
            return;
        }
        try
        {
            var reply = await _bridge.SendAsync("CALSTATUS");
            if (!LightGuardAppAdapter.TryParseCalStatus(reply, out var board) || board is null || board.Count != 6)
                throw new InvalidOperationException("CALSTATUS ناقص یا نامعتبر است.");
            foreach (var profile in LightStateProfiles)
            {
                if (!board.Profiles.TryGetValue(profile.Id, out var device))
                    throw new InvalidOperationException("پروفایل برد ناقص: " + profile.Id);
                profile.LuxCenter = device.Center;
                profile.LuxTolerance = device.Tolerance;
                profile.StableDurationMs = device.StableMs;
            }
            LightStateProfileStore.Save(LightStateProfiles.ToList());
            _lightStateClassifier = new LightStateClassifier(LightStateProfiles);
            RefreshLightGateDiagnosticProfiles();
            RefreshLightGuardProfileDisplays();
            LightGuardCalibrationSynchronized = false;
            LightStateWarning = DescribeProfileOverlaps(LightStateProfiles);
            LightProfileSaveStatus = "کالیبراسیون از Pico دریافت و در پروفایل‌های برنامه ذخیره شد.";
            LightGuardCalibrationStatus = "دریافت از Pico موفق شد؛ برای تأیید دوطرفه هنوز ارسال به Pico را اجرا نکنید.";
            Log("phase7 Guard: calibration pulled from Pico and saved to app profiles");
        }
        catch (Exception ex)
        {
            LightGuardCalibrationStatus = "دریافت از Pico ناموفق — fail closed: " + ex.Message;
            Log("phase7 Guard pull failed: " + ex.Message);
        }
    }

    public async Task SyncLightGuardCalibrationAsync()
    {
        InitializeLightGuardAdapter();
        LightGuardCalibrationSynchronized = false;
        if (_bridge is null || Connection != ConnectionState.Connected)
        {
            LightGuardCalibrationStatus = "همگام‌سازی مسدود شد: برد متصل نیست.";
            return;
        }
        await RefreshLightGuardIdentityAsync();
        if (!LightGuardIdentityValid) return;

        try
        {
            var revision = LightGuardAppAdapter.ComputeRevision(LightStateProfiles);
            foreach (var profileId in LightGuardCalibrationProtocol.ProfileIds)
            {
                var profile = LightStateProfiles.FirstOrDefault(x => x.Id == profileId);
                if (profile is null) throw new InvalidOperationException("پروفایل ناقص: " + profileId);
                // CALSET persists the complete six-profile bundle and rebuilds its hash manifest
                // on the Pico filesystem. It is intentionally longer than the 5s bridge default.
                var reply = await _bridge.SendAsync(
                    LightGuardAppAdapter.BuildCalSet(revision, profile),
                    timeoutSeconds: 30);
                if (!reply.StartsWith("OK|CALSET|", StringComparison.Ordinal))
                    throw new InvalidOperationException($"CALSET {profileId} رد شد: {reply}");
            }
            var check = await _bridge.SendAsync("CALGET");
            if (!LightGuardAppAdapter.TryParseCalGet(check, out var device) || device is null
                || device.Count != 6 || device.Revision != revision)
                throw new InvalidOperationException("تأیید نهایی CALGET با revision برنامه یکسان نیست.");
            LightGuardCalibrationSynchronized = true;
            LightGuardRevisionDisplay = $"نسخهٔ Pico: {device.Revision} · رکوردها: {device.Count}/6 · نسخهٔ برنامه: {revision}";
            LightGuardRevisionComparison = "همگام‌سازی موفق؛ شش رکورد با یک revision ذخیره و تأیید شد.";
            LightGuardCalibrationStatus = "شش پروفایل با موفقیت به Pico Guard ارسال و تأیید شدند.";
            Log("phase7 Guard: six CALSET records synchronized and verified");
        }
        catch (Exception ex)
        {
            LightGuardCalibrationSynchronized = false;
            LightGuardCalibrationStatus = "همگام‌سازی ناقص/ناموفق — fail closed: " + ex.Message;
            LightGuardRevisionComparison = "revision نامطمئن است؛ دوباره CALGET و Sync را بررسی کنید.";
            Log("phase7 Guard CALSET failed: " + ex.Message);
        }
    }

    public async Task CompareLightGuardCalibrationAsync()
    {
        InitializeLightGuardAdapter();
        if (_bridge is null || Connection != ConnectionState.Connected)
        {
            LightGuardComparisonStatus = "مقایسه انجام نشد: برد متصل نیست.";
            return;
        }
        try
        {
            var reply = await _bridge.SendAsync("CALSTATUS");
            if (!LightGuardAppAdapter.TryParseCalStatus(reply, out var board) || board is null || board.Count != 6)
                throw new InvalidOperationException("CALSTATUS ناقص یا نامعتبر است.");
            LightGuardComparisonDisplays.Clear();
            var same = 0;
            foreach (var id in LightGuardCalibrationProtocol.ProfileIds)
            {
                var app = LightStateProfiles.FirstOrDefault(x => x.Id == id);
                var hasBoard = app is not null && board.Profiles.TryGetValue(id, out var device);
                var equal = hasBoard && NearlyEqual(app!.LuxCenter, device!.Center)
                    && NearlyEqual(app.LuxTolerance, device.Tolerance)
                    && app.StableDurationMs == device.StableMs;
                if (equal) same++;
                var boardText = hasBoard
                    ? $"مرکز {device!.Center:0.###} · تلورانس ±{device.Tolerance:0.###} · ثبات {device.StableMs}ms"
                    : "در Pico موجود نیست";
                var appText = app is null
                    ? "در برنامه موجود نیست"
                    : $"مرکز {app.LuxCenter:0.###} · تلورانس ±{app.LuxTolerance:0.###} · ثبات {app.StableDurationMs}ms";
                LightGuardComparisonDisplays.Add($"{id} · برنامه: {appText} · Pico: {boardText} · {(equal ? "یکسان" : "متفاوت")}");
            }
            LightGuardComparisonStatus = same == 6
                ? "مقایسه موفق: هر ۶ پروفایل کاملاً یکسان هستند."
                : $"مقایسه انجام شد: {same}/6 یکسان؛ موارد باقی‌مانده نیاز به اصلاح یا Sync دارند.";
            Log($"phase7 Guard compare: {same}/6 profiles match");
        }
        catch (Exception ex)
        {
            LightGuardComparisonStatus = "مقایسه ناموفق — fail closed: " + ex.Message;
            Log("phase7 Guard compare failed: " + ex.Message);
        }
    }

    private static bool NearlyEqual(double a, double b) => Math.Abs(a - b) <= 0.0005;

    public async Task EnableLightGuardAsync()
    {
        await SendGuardObservationCommandAsync("GUARD|ON", "پایش Guard روشن شد؛ سنسور فقط مشاهده می‌کند.");
    }

    public async Task DisableLightGuardAsync()
    {
        await SendGuardObservationCommandAsync("GUARD|OFF", "پایش Guard خاموش شد.");
    }

    private async Task SendGuardObservationCommandAsync(string command, string success)
    {
        InitializeLightGuardAdapter();
        if (_bridge is null || Connection != ConnectionState.Connected)
        {
            LightGuardObservationStatus = "فرمان Guard رد شد: برد متصل نیست.";
            return;
        }
        if (!LightGuardIdentityValid)
        {
            LightGuardObservationStatus = "فرمان Guard مسدود شد: ابتدا هویت Guard را Refresh کنید.";
            return;
        }
        if (command == "GUARD|ON" && !LightGuardCalibrationSynchronized)
        {
            LightGuardObservationStatus = "Guard ON مسدود شد: ابتدا هر شش CALSET را Sync و تأیید کنید.";
            return;
        }
        try
        {
            var reply = await _bridge.SendAsync(command);
            if (!reply.StartsWith("OK|GUARD|", StringComparison.Ordinal))
                throw new InvalidOperationException(reply);
            LightGuardObservationEnabled = command.EndsWith("ON", StringComparison.Ordinal);
            LightGuardObservationStatus = success;
            Log("phase7 Guard: " + command);
        }
        catch (Exception ex)
        {
            LightGuardObservationEnabled = false;
            LightGuardObservationStatus = "فرمان Guard ناموفق — fail closed: " + ex.Message;
            Log("phase7 Guard command failed: " + ex.Message);
        }
    }

    private void RefreshLightGuardProfileDisplays()
    {
        LightGuardProfileDisplays.Clear();
        foreach (var id in LightGuardCalibrationProtocol.ProfileIds)
        {
            var profile = LightStateProfiles.FirstOrDefault(x => x.Id == id);
            LightGuardProfileDisplays.Add(profile is null
                ? $"{id}: ناقص"
                : $"{id} · مرکز {profile.LuxCenter:0.###} · تلورانس ±{profile.LuxTolerance:0.###} · ثبات {profile.StableDurationMs}ms");
        }
        OnPropertyChanged(nameof(LightGuardProfileDisplays));
    }

    private void OnLightGuardBridgeLine(object? sender, string line)
    {
        if (!LightGuardAppAdapter.TryExtractEventLine(line, out var eventLine)) return;
        RunOnUi(() => ApplyLightGuardEvent(eventLine));
    }

    private void ApplyLightGuardEvent(string line)
    {
        if (LightGuardAppAdapter.TryParseCalibrationEvent(line, out var calibration) && calibration is not null)
        {
            var stage = calibration.Stage is int s ? $"مرحله {s}/6" : "کالیبراسیون";
            if (calibration.Mode is "complete" or "cancelled")
                LightGuardCalibrationSynchronized = false;
            LightGuardCalibrationStatus = calibration.Mode switch
            {
                "ready" => $"{stage}: جایگاه «{calibration.ProfileId}» آماده؛ GP3 را فشار دهید.",
                "started" => $"{stage}: نمونه‌برداری پنج‌ثانیه‌ای برای «{calibration.ProfileId}» در حال انجام است.",
                "complete-stage" => $"{stage}: ذخیره شد · مرکز {calibration.Center:0.0} · spread {calibration.Spread:0.0} · تلورانس ±{calibration.Tolerance:0.0}",
                "complete" => $"کالیبراسیون شش‌مرحله‌ای کامل شد · revision {calibration.Revision}; اکنون Sync برنامه را اجرا کنید.",
                "cancelled" => "کالیبراسیون فیزیکی لغو شد؛ آخرین مجموعهٔ کامل حفظ می‌شود.",
                _ => "رویداد کالیبراسیون دریافت شد: " + calibration.Mode,
            };
            Log("phase7 Guard calibration: " + line);
            return;
        }
        if (line.Contains("enabled=true", StringComparison.Ordinal))
        {
            LightGuardObservationEnabled = true;
            LightGuardObservationStatus = "پایش Guard روشن است.";
        }
        else if (line.Contains("enabled=false", StringComparison.Ordinal))
        {
            LightGuardObservationEnabled = false;
            LightGuardObservationStatus = "پایش Guard خاموش است.";
        }
        if (LightGuardCalibrationProtocol.TryParseStateEvent(line, out var state) && state is not null)
        {
            LightGuardStateDisplay = $"{state.ProfileId} · {state.Lux:0.0} Lux · revision {state.Revision}";
            LightGuardObservationStatus = "رویداد پایدار Guard دریافت شد؛ هیچ pipeline یا execution فراخوانی نشد.";
        }
        else if (line.Contains("state=unknown", StringComparison.Ordinal))
        {
            LightGuardStateDisplay = "نامشخص — تطبیق مبهم یا بدون match";
        }
        Log("phase7 Guard event: " + line);
    }
}
