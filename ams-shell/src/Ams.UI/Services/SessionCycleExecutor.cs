using System;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;

namespace Ams.UI.Services;

public sealed record SessionCycleExecutionRequest(
    SessionCycleState State,
    PipelineKind Pipeline,
    bool ConfigureBootLoader,
    bool IsRecovery,
    string Reason);

/// <summary>
/// Narrow side-effect boundary for the session cycle. Implementations may later
/// call RunEngine or Windows controls, but the orchestrator never does so directly.
/// </summary>
public interface ISessionCycleExecutor
{
    Task ConfigureBootLoaderAsync(CancellationToken cancellationToken = default);
    Task RunPipelineAsync(SessionCycleExecutionRequest request, CancellationToken cancellationToken = default);
    Task RequestRestartAsync(CancellationToken cancellationToken = default);
}

/// <summary>
/// Default safe executor used until the real Windows/RunEngine adapter is explicitly enabled.
/// It records no side effects and fails closed instead of starting a game cycle accidentally.
/// </summary>
public sealed class DisabledSessionCycleExecutor : ISessionCycleExecutor
{
    public Task ConfigureBootLoaderAsync(CancellationToken cancellationToken = default)
        => Task.FromException(new InvalidOperationException("Session cycle executor is disabled."));

    public Task RunPipelineAsync(SessionCycleExecutionRequest request, CancellationToken cancellationToken = default)
        => Task.FromException(new InvalidOperationException("Session cycle executor is disabled."));

    public Task RequestRestartAsync(CancellationToken cancellationToken = default)
        => Task.FromException(new InvalidOperationException("Session cycle executor is disabled."));
}
