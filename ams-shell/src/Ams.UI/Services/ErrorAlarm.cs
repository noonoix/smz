using System.Media;

namespace Ams.UI.Services;

/// <summary>Cancellable PC-side fallback alarm. Pico-side alarms remain local to the portable
/// runtime; this class is used when the host still has a usable audio device.</summary>
public sealed class ErrorAlarm : IDisposable
{
    private readonly CancellationTokenSource _cts = new();
    private readonly Task _loop;

    private ErrorAlarm(ErrorPolicySettings policy)
    {
        _loop = Task.Run(async () =>
        {
            var until = policy.AlarmDurationSeconds > 0
                ? DateTimeOffset.UtcNow.AddSeconds(policy.AlarmDurationSeconds)
                : DateTimeOffset.MaxValue;
            do
            {
                try { SystemSounds.Exclamation.Play(); } catch { }
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
