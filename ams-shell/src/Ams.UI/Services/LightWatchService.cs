using System.Diagnostics;

using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Cancellation-safe polling loop for read-only light telemetry. Calls are awaited serially,
/// so the service can never overlap LUX? requests or bypass the bridge command lock.
/// </summary>
public sealed class LightWatchService : IAsyncDisposable
{
    public const int DefaultIntervalMs = 250;
    private static readonly HashSet<int> AllowedIntervalsMs = new() { 100, 250, 500, 1000 };
    private readonly IBoardBridge _bridge;
    private readonly object _gate = new();
    private CancellationTokenSource? _runCts;
    private Task? _runner;
    private Task? _stopTask;

    public LightWatchService(IBoardBridge bridge) => _bridge = bridge ?? throw new ArgumentNullException(nameof(bridge));

    public event Action<LightTelemetrySample>? SampleReceived;
    public event Action<Exception>? WatchFaulted;

    public bool IsRunning
    {
        get { lock (_gate) return _runner is { IsCompleted: false }; }
    }

    public static TimeSpan GetStaleThreshold(TimeSpan sampleInterval)
    {
        if (sampleInterval <= TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(sampleInterval));
        return TimeSpan.FromMilliseconds(Math.Max(2000, sampleInterval.TotalMilliseconds * 3));
    }

    public Task StartAsync(TimeSpan interval, CancellationToken ct = default)
    {
        var intervalMs = checked((int)interval.TotalMilliseconds);
        if (!AllowedIntervalsMs.Contains(intervalMs) || interval != TimeSpan.FromMilliseconds(intervalMs))
            throw new ArgumentOutOfRangeException(nameof(interval), "Interval must be exactly 100, 250, 500, or 1000 ms.");
        if (_bridge.State != BridgeState.Connected)
            throw new InvalidOperationException("Bridge must be connected before Watch starts.");

        lock (_gate)
        {
            if (_stopTask is not null)
                throw new InvalidOperationException("Light Watch is still stopping.");
            if (_runner is { IsCompleted: false })
                throw new InvalidOperationException("Light Watch is already running.");
            _runCts?.Dispose();
            _runCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            _runner = RunAsync(interval, _runCts.Token);
        }
        return Task.CompletedTask;
    }

    public Task StopAsync()
    {
        lock (_gate)
        {
            if (_stopTask is not null) return _stopTask;

            var runner = _runner;
            var cts = _runCts;
            cts?.Cancel();

            var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            _stopTask = completion.Task;
            _ = StopCoreAsync(runner, cts, completion);
            return completion.Task;
        }
    }

    private async Task StopCoreAsync(
        Task? runner,
        CancellationTokenSource? cts,
        TaskCompletionSource completion)
    {
        try
        {
            if (runner is not null)
            {
                // Light Watch is read-only telemetry. Cancellation is enough to unwind the
                // in-flight LUX? request; do not send the global HALT/abort command here.
                // HALT is reserved for an actual Guard/Run stop and intentionally plays the
                // board Stop cue. Stopping the sensor chart must be silent and must not alter
                // Guard state.
                try { await runner.ConfigureAwait(false); }
                catch (OperationCanceledException) { }
            }
        }
        finally
        {
            lock (_gate)
            {
                if (ReferenceEquals(_runner, runner))
                {
                    _runner = null;
                    _runCts = null;
                    cts?.Dispose();
                }
                _stopTask = null;
            }
            completion.TrySetResult();
        }
    }

    private async Task RunAsync(TimeSpan interval, CancellationToken ct)
    {
        while (!ct.IsCancellationRequested && _bridge.State == BridgeState.Connected)
        {
            var elapsed = Stopwatch.StartNew();
            try
            {
                var sample = await _bridge.ReadLightAsync(ct).ConfigureAwait(false);
                SampleReceived?.Invoke(sample);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                WatchFaulted?.Invoke(ex);
            }

            var remaining = interval - elapsed.Elapsed;
            if (remaining > TimeSpan.Zero)
                await Task.Delay(remaining, ct).ConfigureAwait(false);
        }
    }

    public async ValueTask DisposeAsync() => await StopAsync().ConfigureAwait(false);
}
