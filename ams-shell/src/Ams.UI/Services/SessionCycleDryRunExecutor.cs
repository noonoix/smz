using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Safe first host implementation for integration testing. It records the exact
/// actions the real executor would receive but never touches Windows, HID, Pico,
/// RunEngine or the boot loader.
/// </summary>
public sealed class SessionCycleDryRunExecutor : ISessionCycleExecutor
{
    private readonly Action<string> _log;
    private readonly List<string> _events = new();
    private readonly object _gate = new();

    public SessionCycleDryRunExecutor(Action<string>? log = null) => _log = log ?? (_ => { });

    public IReadOnlyList<string> Events
    {
        get { lock (_gate) return _events.ToArray(); }
    }

    public Task ConfigureBootLoaderAsync(CancellationToken cancellationToken = default)
        => RecordAsync("dry-run: configure Windows Boot Loader once", cancellationToken);

    public Task RunPipelineAsync(SessionCycleExecutionRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        return RecordAsync($"dry-run: pipeline={request.Pipeline};cycle={request.State.CycleNumber};recovery={request.IsRecovery};reason={request.Reason}", cancellationToken);
    }

    public Task RequestRestartAsync(CancellationToken cancellationToken = default)
        => RecordAsync("dry-run: request Windows restart", cancellationToken);

    private Task RecordAsync(string message, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (_gate) _events.Add(message);
        _log(message);
        return Task.CompletedTask;
    }
}
