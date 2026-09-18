using System;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private readonly SessionCycleOrchestrator _sessionCycle = new();
    private CancellationTokenSource? _sessionCycleDryRunCts;
    private string _sessionCycleDryRunStatus = "چرخهٔ جلسه اجرا نشده است.";
    private bool _sessionCycleDryRunRunning;

    public string SessionCycleDryRunStatus
    {
        get => _sessionCycleDryRunStatus;
        private set => SetProperty(ref _sessionCycleDryRunStatus, value);
    }

    public bool SessionCycleDryRunRunning
    {
        get => _sessionCycleDryRunRunning;
        private set => SetProperty(ref _sessionCycleDryRunRunning, value);
    }

    /// <summary>
    /// Runs the complete five-cycle contract without Windows input, reboot, RunEngine,
    /// HID, Pico writes, or boot-loader changes. It is deliberately the only host path
    /// exposed while the real executor remains disabled.
    /// </summary>
    public async Task RunSessionCycleDryRunAsync()
    {
        if (SessionCycleDryRunRunning) return;
        _sessionCycleDryRunCts = new CancellationTokenSource();
        SessionCycleDryRunRunning = true;
        try
        {
            var executor = new SessionCycleDryRunExecutor(Log);
            var start = _sessionCycle.Start();
            if (!start.Accepted) throw new InvalidOperationException(start.Reason);
            UpdateSessionCycleStatus(start.State, start.Reason);

            var boot = _sessionCycle.MarkBootLoaderConfigured();
            if (!boot.Accepted) throw new InvalidOperationException(boot.Reason);
            await executor.ConfigureBootLoaderAsync(_sessionCycleDryRunCts.Token);
            UpdateSessionCycleStatus(boot.State, boot.Reason);

            while (_sessionCycle.State.Running)
            {
                var state = _sessionCycle.State;
                await RunDryPipelineAsync(executor, PipelineKind.Desktop, false, "desktop start", state);
                await ObserveAndRunAsync(executor, "login-or-dc", PipelineKind.LoginOrDc, false, "normal login", false);
                await ObserveAndRunAsync(executor, "character-dashboard", PipelineKind.CharacterDashboard, false, "dashboard", false);
                await ObserveAndRunAsync(executor, "entering-game-loading", PipelineKind.EnteringGameLoading, false, "loading", false);
                await ObserveAndRunAsync(executor, "game", PipelineKind.Game, false, "game", false);

                var resumable = _sessionCycle.StartResumable();
                if (!resumable.Accepted) throw new InvalidOperationException(resumable.Reason);
                UpdateSessionCycleStatus(resumable.State, resumable.Reason);
                await RunDryPipelineAsync(executor, PipelineKind.Resumable, false, "resume essentials", resumable.State);
                var resumed = _sessionCycle.CompleteResumable();
                if (!resumed.Accepted) throw new InvalidOperationException(resumed.Reason);
                UpdateSessionCycleStatus(resumed.State, resumed.Reason);
                await RunDryPipelineAsync(executor, PipelineKind.Game, true, "returned from Resumable", resumed.State);

                var targeted = _sessionCycle.ObserveProfile("targeted");
                if (!targeted.Accepted) throw new InvalidOperationException(targeted.Reason);
                UpdateSessionCycleStatus(targeted.State, targeted.Reason);
                await RunDryPipelineAsync(executor, PipelineKind.Targeted, false, "targeted side-state", targeted.State);
                var backToGame = _sessionCycle.ObserveProfile("game");
                if (!backToGame.Accepted) throw new InvalidOperationException(backToGame.Reason);
                UpdateSessionCycleStatus(backToGame.State, backToGame.Reason);
                await RunDryPipelineAsync(executor, PipelineKind.Game, true, "targeted returned to game", backToGame.State);

                var restart = _sessionCycle.RequestRestart();
                if (!restart.Accepted) throw new InvalidOperationException(restart.Reason);
                UpdateSessionCycleStatus(restart.State, restart.Reason);
                if (!restart.State.Running) break;
                var issued = _sessionCycle.MarkRestartIssued();
                if (!issued.Accepted) throw new InvalidOperationException(issued.Reason);
                await executor.RequestRestartAsync(_sessionCycleDryRunCts.Token);
                UpdateSessionCycleStatus(issued.State, issued.Reason);
                var rebooted = _sessionCycle.ObserveRebootedDesktop();
                if (!rebooted.Accepted) throw new InvalidOperationException(rebooted.Reason);
                UpdateSessionCycleStatus(rebooted.State, rebooted.Reason);
            }

            SessionCycleDryRunStatus = "dry-run کامل شد: پنج چرخه بدون هیچ side effect واقعی.";
            Log("session cycle dry-run completed: five cycles; no Windows/Pico/RunEngine side effect");
        }
        catch (OperationCanceledException)
        {
            _sessionCycle.Stop("dry-run cancelled");
            SessionCycleDryRunStatus = "dry-run لغو شد.";
            Log("session cycle dry-run cancelled");
        }
        catch (Exception ex)
        {
            _sessionCycle.Fault(ex.Message);
            SessionCycleDryRunStatus = "dry-run متوقف شد: " + ex.Message;
            Log("session cycle dry-run failed: " + ex.Message);
        }
        finally
        {
            _sessionCycleDryRunCts?.Dispose();
            _sessionCycleDryRunCts = null;
            SessionCycleDryRunRunning = false;
        }
    }

    public void CancelSessionCycleDryRun()
    {
        if (SessionCycleDryRunRunning) _sessionCycleDryRunCts?.Cancel();
    }

    private async Task ObserveAndRunAsync(SessionCycleDryRunExecutor executor, string profile,
        PipelineKind pipeline, bool recovery, string reason, bool ignored)
    {
        var transition = _sessionCycle.ObserveProfile(profile);
        if (!transition.Accepted) throw new InvalidOperationException(transition.Reason);
        UpdateSessionCycleStatus(transition.State, transition.Reason);
        await RunDryPipelineAsync(executor, pipeline, recovery, reason, transition.State);
    }

    private async Task RunDryPipelineAsync(SessionCycleDryRunExecutor executor, PipelineKind pipeline,
        bool recovery, string reason, SessionCycleState state)
    {
        await executor.RunPipelineAsync(new SessionCycleExecutionRequest(
            state, pipeline, ConfigureBootLoader: false, IsRecovery: recovery, Reason: reason),
            _sessionCycleDryRunCts?.Token ?? CancellationToken.None);
        SessionCycleDryRunStatus = $"dry-run · چرخه {state.CycleNumber}/{state.MaximumCycles} · {pipeline} · {reason}";
    }

    private void UpdateSessionCycleStatus(SessionCycleState state, string reason)
    {
        SessionCycleDryRunStatus = $"dry-run · چرخه {state.CycleNumber}/{state.MaximumCycles} · مرحله {state.Phase} · {reason}";
    }
}
