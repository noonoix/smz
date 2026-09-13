namespace Ams.UI.Services;

/// <summary>Cancellable PC-side fallback alarm. The portable runtime owns Pico-side alarms; this host fallback uses a framework console signal so it does not require an extra audio assembly reference during the Windows build.</summary>
public sealed class ErrorAlarm : IDisposable
{
    private readonly CancellationTokenSource _cts = new();
    private readonly Task _loop;

    private ErrorAlarm(ErrorPolicySettings policy)
    {
        _loop = Task.Run(async () =>
        {
            var until = policy.AlarmDurationSeconds > 0 ? DateTimeOffset.UtcNow.AddSeconds(policy.AlarmDurationSeconds) : DateTimeOffset.MaxValue;
            do
            {
                try { Console.Beep(880, 180); } catch { }
                if (!policy.RepeatAlarm) break;
                await Task.Delay(850, _cts.Token);
            } while (DateTimeOffset.UtcNow < until && !_cts.IsCancellationRequested);
        }, _cts.Token);
    }

    public static ErrorAlarm? Start(ErrorPolicySettings policy)
        => policy.FatalAlarmEnabled && policy.AlarmSource is "pc" or "both" ? new ErrorAlarm(policy) : null;

    public void Dispose()
    {
        if (_cts.IsCancellationRequested) return;
        _cts.Cancel();
        try { _loop.Wait(250); } catch { }
        _cts.Dispose();
    }
}
