using System.Runtime.CompilerServices;
using System.Windows;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.UI.ViewModels;

/// <summary>Phase 7 execution bridge. Guard remains fail-closed until identity, calibration,
/// observation and pipeline revisions are all valid. The transition planner owns one-shot state;
/// this partial only selects the requested visible tab and enters the existing Run command.</summary>
public partial class MainViewModel
{
    private bool _lightGuardExecutionHooked;
    private readonly LightGuardTransitionController _lightGuardTransitionController = new();
    private string _lightGuardExpectedPipelineRevision = string.Empty;
    private bool _lightGuardExecutionInFlight;
    private string _lightGuardExecutionStatus = "اجرای خودکار Guard خاموش است.";

    public string LightGuardExecutionStatus
    {
        get => _lightGuardExecutionStatus;
        private set => SetProperty(ref _lightGuardExecutionStatus, value);
    }

    public void InitializeLightGuardExecution()
    {
        if (_lightGuardExecutionHooked || _bridge is null) return;
        _bridge.LineReceived += OnLightGuardExecutionLine;
        _lightGuardExecutionHooked = true;
        Log("phase7 Guard execution boundary initialized: fail-closed");
    }

    private void OnLightGuardExecutionLine(object? sender, string line)
    {
        if (!LightGuardAppAdapter.TryExtractEventLine(line, out var eventLine)) return;
        RunOnUi(() => ApplyLightGuardExecutionEvent(eventLine));
    }

    private void ApplyLightGuardExecutionEvent(string line)
    {
        if (line.Contains("enabled=false", StringComparison.Ordinal))
        {
            _lightGuardTransitionController.Reset();
            _lightGuardExpectedPipelineRevision = string.Empty;
            LightGuardExecutionStatus = "Guard خاموش است؛ اجرای pipeline متوقف شد.";
            return;
        }

        if (line.Contains("enabled=true", StringComparison.Ordinal))
        {
            if (!LightGuardIdentityValid || !LightGuardCalibrationSynchronized)
            {
                _lightGuardTransitionController.Reset();
                LightGuardExecutionStatus = "اجرای Guard مسدود شد: هویت یا Sync کالیبراسیون معتبر نیست.";
                return;
            }
            try
            {
                _lightGuardExpectedPipelineRevision = CurrentLightGuardPipelineRevision();
                _lightGuardTransitionController.Reset();
                LightGuardExecutionStatus = "Guard روشن است؛ اجرای انتقال‌ها با revision قفل شد.";
                Log("phase7 Guard execution armed at pipeline revision " + _lightGuardExpectedPipelineRevision);
            }
            catch (Exception ex)
            {
                _lightGuardExpectedPipelineRevision = string.Empty;
                _lightGuardTransitionController.Reset();
                LightGuardExecutionStatus = "اجرای Guard مسدود شد: revision pipeline قابل محاسبه نیست.";
                Log("phase7 Guard pipeline revision failed: " + ex.Message);
            }
            return;
        }

        if (!LightGuardCalibrationProtocol.TryParseStateEvent(line, out var state) || state is null) return;
        if (!LightGuardObservationEnabled || !LightGuardIdentityValid || !LightGuardCalibrationSynchronized)
        {
            LightGuardExecutionStatus = "رویداد Guard دریافت شد، اما execution gate بسته است.";
            return;
        }
        if (string.IsNullOrWhiteSpace(_lightGuardExpectedPipelineRevision))
        {
            LightGuardExecutionStatus = "رویداد Guard رد شد: pipeline revision در این جلسه قفل نشده است.";
            return;
        }

        string currentPipelineRevision;
        string profileRevision;
        try
        {
            currentPipelineRevision = CurrentLightGuardPipelineRevision();
            profileRevision = LightGuardAppAdapter.ComputeRevision(LightStateProfiles);
        }
        catch (Exception ex)
        {
            LightGuardExecutionStatus = "رویداد Guard رد شد: revision قابل تأیید نیست.";
            Log("phase7 Guard execution revision check failed: " + ex.Message);
            return;
        }

        var decision = _lightGuardTransitionController.ObserveStable(new LightGuardTransitionInput(
            state.ProfileId,
            state.Revision,
            profileRevision,
            currentPipelineRevision,
            _lightGuardExpectedPipelineRevision,
            ObservationEnabled: true,
            CalibrationSynchronized: LightGuardCalibrationSynchronized,
            ConnectionHealthy: Connection == ConnectionState.Connected));

        if (!decision.ShouldExecute)
        {
            LightGuardExecutionStatus = "Guard transition rejected: " + decision.Reason;
            Log("phase7 Guard transition rejected: " + state.ProfileId + " — " + decision.Reason);
            return;
        }

        if (!TryStartLightGuardPipeline(decision))
            _lightGuardTransitionController.ObserveUnknown();
    }

    private bool TryStartLightGuardPipeline(LightGuardTransitionDecision decision)
    {
        if (decision.Pipeline is not PipelineKind pipeline)
        {
            LightGuardExecutionStatus = "Guard transition rejected: no pipeline mapping.";
            return false;
        }
        if (_lightGuardExecutionInFlight || IsRunning || _runActive)
        {
            LightGuardExecutionStatus = "Guard transition rejected: another run is active.";
            Log("phase7 Guard execution rejected: RunEngine already active");
            return false;
        }

        try
        {
            var currentRevision = CurrentLightGuardPipelineRevision();
            if (!string.Equals(currentRevision, _lightGuardExpectedPipelineRevision, StringComparison.Ordinal))
            {
                LightGuardExecutionStatus = "Guard transition rejected: pipeline changed after authorization.";
                Log("phase7 Guard execution rejected: pipeline revision changed");
                return false;
            }

            InitializePipelineTabs();
            var tab = _pipelineWorkspace[pipeline];
            if (!ReferenceEquals(_activePipelineTab, tab))
            {
                if (!SwitchPipelineCommand.CanExecute(tab))
                {
                    LightGuardExecutionStatus = "Guard transition rejected: pipeline tab cannot be selected.";
                    return false;
                }
                SwitchPipelineCommand.Execute(tab);
            }
            if (!RunCommand.CanExecute(null))
            {
                LightGuardExecutionStatus = "Guard transition rejected: RunEngine is not ready.";
                return false;
            }

            _lightGuardExecutionInFlight = true;
            LightGuardExecutionStatus = $"Guard transition approved: {pipeline} · {decision.Context}; Steps شروع شد.";
            Log($"phase7 Guard execution: {pipeline} · context={decision.Context} · {decision.Reason}");
            RunCommand.Execute(null);
            return true;
        }
        catch (Exception ex)
        {
            LightGuardExecutionStatus = "Guard execution failed — fail closed: " + ex.Message;
            Log("phase7 Guard execution failed: " + ex.Message);
            return false;
        }
        finally
        {
            // RunCommand owns the asynchronous run lifetime. This flag only prevents two Guard
            // events from entering the launch boundary in the same UI turn; the planner remains
            // the durable one-shot latch for duplicate stable events.
            _lightGuardExecutionInFlight = false;
        }
    }

    private string CurrentLightGuardPipelineRevision()
    {
        InitializePipelineTabs();
        return PipelineWorkspaceRevision.Compute(CapturePipelineWorkspaceForExport());
    }
}

/// <summary>Hooks the execution bridge after the main window and Guard adapter exist.</summary>
internal static class LightGuardExecutionUiBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.DataContext is not MainViewModel vm) return;
        window.Dispatcher.BeginInvoke(new Action(vm.InitializeLightGuardExecution),
            System.Windows.Threading.DispatcherPriority.ApplicationIdle);
    }
}
