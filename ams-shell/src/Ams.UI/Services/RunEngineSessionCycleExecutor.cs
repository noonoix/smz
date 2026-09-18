using System;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Adapter boundary for connecting the cycle coordinator to RunEngine later.
/// The host supplies the actual pipeline callbacks and a revision/authorization
/// check; this class never guesses a pipeline or bypasses cancellation.
/// </summary>
public sealed class RunEngineSessionCycleExecutor : ISessionCycleExecutor, IAsyncDisposable
{
    private readonly Func<CancellationToken, Task> _configureBootLoader;
    private readonly Func<PipelineKind, SessionCycleExecutionRequest, CancellationToken, Task> _runPipeline;
    private readonly Func<CancellationToken, Task> _requestRestart;
    private readonly Func<SessionCycleExecutionRequest, bool> _authorize;
    private readonly SemaphoreSlim _serial = new(1, 1);
    private int _disposed;

    public RunEngineSessionCycleExecutor(
        Func<CancellationToken, Task> configureBootLoader,
        Func<PipelineKind, SessionCycleExecutionRequest, CancellationToken, Task> runPipeline,
        Func<CancellationToken, Task> requestRestart,
        Func<SessionCycleExecutionRequest, bool> authorize)
    {
        _configureBootLoader = configureBootLoader ?? throw new ArgumentNullException(nameof(configureBootLoader));
        _runPipeline = runPipeline ?? throw new ArgumentNullException(nameof(runPipeline));
        _requestRestart = requestRestart ?? throw new ArgumentNullException(nameof(requestRestart));
        _authorize = authorize ?? throw new ArgumentNullException(nameof(authorize));
    }

    public Task ConfigureBootLoaderAsync(CancellationToken cancellationToken = default)
        => RunExclusiveAsync(_configureBootLoader, cancellationToken);

    public Task RunPipelineAsync(SessionCycleExecutionRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (!_authorize(request))
            return Task.FromException(new InvalidOperationException("Session cycle execution authorization rejected."));
        return RunExclusiveAsync(ct => _runPipeline(request.Pipeline, request, ct), cancellationToken);
    }

    public Task RequestRestartAsync(CancellationToken cancellationToken = default)
        => RunExclusiveAsync(_requestRestart, cancellationToken);

    private async Task RunExclusiveAsync(Func<CancellationToken, Task> operation, CancellationToken cancellationToken)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        await _serial.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            await operation(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _serial.Release();
        }
    }

    public ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0) _serial.Dispose();
        return ValueTask.CompletedTask;
    }
}
