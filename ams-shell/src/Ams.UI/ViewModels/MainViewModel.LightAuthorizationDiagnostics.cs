using Ams.UI.Services;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private static readonly IReadOnlyList<(string Label, LightExecutionIntent Intent)> AuthorizationIntentMap =
        new (string, LightExecutionIntent)[]
        {
            ("دسکتاپ", LightExecutionIntent.Desktop),
            ("داشبورد شخصیت", LightExecutionIntent.CharacterDashboard),
            ("صفحه بارگذاری", LightExecutionIntent.EnteringGameLoading),
            ("بازی", LightExecutionIntent.Game),
            ("تارگت شدن توسط افراد", LightExecutionIntent.Targeted),
        };

    private readonly NonExecutingLightAuthorizationDiagnostics _lightAuthorizationDiagnostics
        = new(Guid.NewGuid().ToString("N"));
    private string _selectedLightAuthorizationIntent = "دسکتاپ";
    private string _lightAuthorizationDiagnosticDisplay = "غیرفعال · فقط تشخیصی — بدون اجرا";
    private string _lightAuthorizationDiagnosticReasonDisplay = "NotArmed";
    private bool _lightAuthorizationDiagnosticIsActive;

    public IReadOnlyList<string> LightAuthorizationIntentOptions
        => AuthorizationIntentMap.Select(x => x.Label).ToArray();

    public string SelectedLightAuthorizationIntent
    {
        get => _selectedLightAuthorizationIntent;
        set
        {
            if (!SetProperty(ref _selectedLightAuthorizationIntent, value)) return;
            var intent = AuthorizationIntentMap.FirstOrDefault(x => x.Label == value).Intent;
            if (!AuthorizationIntentMap.Any(x => x.Label == value)) intent = (LightExecutionIntent)(-1);
            var snapshot = _lightAuthorizationDiagnostics.SelectIntent(intent);
            LightAuthorizationDiagnosticIsActive = false;
            PublishLightAuthorizationSnapshot(snapshot);
            Log($"light auth diagnostic: intent={intent} reason={snapshot.ReasonCode}");
        }
    }

    public string LightAuthorizationDiagnosticDisplay
    {
        get => _lightAuthorizationDiagnosticDisplay;
        private set => SetProperty(ref _lightAuthorizationDiagnosticDisplay, value);
    }

    public string LightAuthorizationDiagnosticReasonDisplay
    {
        get => _lightAuthorizationDiagnosticReasonDisplay;
        private set => SetProperty(ref _lightAuthorizationDiagnosticReasonDisplay, value);
    }

    public bool LightAuthorizationDiagnosticIsActive
    {
        get => _lightAuthorizationDiagnosticIsActive;
        private set => SetProperty(ref _lightAuthorizationDiagnosticIsActive, value);
    }

    public bool LightAuthorizationDiagnosticCanIssue => _lightAuthorizationDiagnostics.CanIssue;
    public bool LightAuthorizationDiagnosticCanConsume => _lightAuthorizationDiagnostics.CanConsume;
    public bool LightAuthorizationDiagnosticCanRevoke => _lightAuthorizationDiagnosticIsActive;

    public void ArmLightAuthorizationDiagnostic()
    {
        var snapshot = _lightAuthorizationDiagnostics.Arm(CurrentLightAuthorizationContext());
        PublishLightAuthorizationSnapshot(snapshot);
        Log($"light auth diagnostic: arm intent={snapshot.SelectedIntent} reason={snapshot.ReasonCode}");
    }

    public void IssueLightAuthorizationDiagnosticPermit()
    {
        var session = _lightGateCoordinator.ActiveSessionId ?? string.Empty;
        var observation = $"{session}:{_lightGateCoordinator.ProfileRevision}:{LightChartVersion}";
        var snapshot = _lightAuthorizationDiagnostics.Issue(
            CurrentLightAuthorizationContext(), _lightGateCoordinator.LastResult, observation);
        PublishLightAuthorizationSnapshot(snapshot);
        Log($"light auth diagnostic: issue intent={snapshot.SelectedIntent} reason={snapshot.ReasonCode} permit={Short(snapshot.PermitId)}");
    }

    public void ConsumeLightAuthorizationDiagnosticPermit()
    {
        var snapshot = _lightAuthorizationDiagnostics.Consume(CurrentLightAuthorizationContext());
        PublishLightAuthorizationSnapshot(snapshot);
        Log($"light auth diagnostic: consume-without-execution intent={snapshot.SelectedIntent} reason={snapshot.ReasonCode} permit={Short(snapshot.PermitId)}");
    }

    public void RevokeLightAuthorizationDiagnostic(
        LightAuthorizationReasonCode reason = LightAuthorizationReasonCode.PermitRevoked)
    {
        var snapshot = _lightAuthorizationDiagnostics.Revoke(reason);
        PublishLightAuthorizationSnapshot(snapshot);
        Log($"light auth diagnostic: revoke reason={snapshot.ReasonCode}");
    }

    private LightAuthorizationDiagnosticContext CurrentLightAuthorizationContext()
    {
        var workspace = CapturePipelineWorkspaceForExport();
        return new LightAuthorizationDiagnosticContext(
            _lightGateCoordinator.ActiveSessionId ?? string.Empty,
            _lightGateCoordinator.ProfileRevision,
            PipelineWorkspaceRevision.Compute(workspace),
            MonotonicNow(),
            IsLightWatchRunning,
            Connection == ConnectionState.Connected,
            CancellationRequested: false);
    }

    private void PublishLightAuthorizationSnapshot(LightAuthorizationDiagnosticSnapshot snapshot)
    {
        LightAuthorizationDiagnosticReasonDisplay = snapshot.ReasonCode.ToString();
        var permit = string.IsNullOrWhiteSpace(snapshot.PermitId) ? string.Empty : $" · Permit {Short(snapshot.PermitId)}";
        LightAuthorizationDiagnosticDisplay = snapshot.State switch
        {
            LightAuthorizationDiagnosticState.Armed => $"مسلح تشخیصی · {IntentLabel(snapshot.SelectedIntent)} · بدون اجرا",
            LightAuthorizationDiagnosticState.PermitIssued => $"Permit تشخیصی صادر شد{permit} · بدون اجرا",
            LightAuthorizationDiagnosticState.PermitConsumed => $"Permit فقط در Ledger مصرف شد{permit} · هیچ اجرایی انجام نشد",
            LightAuthorizationDiagnosticState.Revoked => "مجوز تشخیصی باطل شد · بدون اجرا",
            LightAuthorizationDiagnosticState.Denied => "رد مجوز تشخیصی · " + DescribeAuthorizationReason(snapshot.ReasonCode),
            _ => "غیرفعال · فقط تشخیصی — بدون اجرا",
        };
        LightAuthorizationDiagnosticIsActive = snapshot.IsArmed;
        OnPropertyChanged(nameof(LightAuthorizationDiagnosticCanIssue));
        OnPropertyChanged(nameof(LightAuthorizationDiagnosticCanConsume));
        OnPropertyChanged(nameof(LightAuthorizationDiagnosticCanRevoke));
    }

    private static string IntentLabel(LightExecutionIntent intent)
        => AuthorizationIntentMap.FirstOrDefault(x => x.Intent == intent).Label ?? intent.ToString();

    private static string DescribeAuthorizationReason(LightAuthorizationReasonCode reason)
        => reason switch
        {
            LightAuthorizationReasonCode.NotArmed => "ابتدا Arm تشخیصی را بزنید",
            LightAuthorizationReasonCode.ArmExpired => "مهلت Arm تمام شده است",
            LightAuthorizationReasonCode.ArmIntentMismatch => "هدف انتخابی تغییر کرده است",
            LightAuthorizationReasonCode.GateDenied => "گیت نور واجد شرایط نیست",
            LightAuthorizationReasonCode.GateReasonMismatch => "هدف گیت با هدف انتخابی منطبق نیست",
            LightAuthorizationReasonCode.Cancelled => "لغوشده",
            LightAuthorizationReasonCode.Disconnected => "پایش یا اتصال متوقف است",
            LightAuthorizationReasonCode.InvalidTime => "زمان monotonic نامعتبر است",
            LightAuthorizationReasonCode.StaleGateResult => "نتیجهٔ گیت قدیمی است",
            LightAuthorizationReasonCode.WatchSessionChanged => "نشست پایش تغییر کرده است",
            LightAuthorizationReasonCode.ProfileChanged => "پروفایل تغییر کرده است",
            LightAuthorizationReasonCode.PipelineChanged => "Pipeline تغییر کرده است؛ دوباره Arm کنید",
            LightAuthorizationReasonCode.ObservationAlreadyAuthorized => "برای این نمونه قبلاً Permit صادر شده است",
            LightAuthorizationReasonCode.IntentNotAllowed => "این هدف در diagnostics مجاز نیست",
            LightAuthorizationReasonCode.PermitUnknown => "Permit فعالی وجود ندارد",
            LightAuthorizationReasonCode.PermitExpired => "مهلت Permit تمام شده است",
            LightAuthorizationReasonCode.AlreadyConsumed => "Permit قبلاً مصرف شده است",
            _ => reason.ToString(),
        };

    private static string Short(string? value)
        => string.IsNullOrWhiteSpace(value) ? "—" : value[..Math.Min(8, value.Length)];
}
