namespace Ams.UI.Services;

/// <summary>Cancellable PC/Pico fallback alarm. The portable runtime owns Pico-side alarms;
/// the desktop runner can provide a Pico beep callback for an active board connection.</summary>
public sealed class ErrorAlarm : IDisposable
{
    private readonly CancellationTokenSource _cts = new();
    private readonly Task _loop;
    private readonly Func<Task>? _picoBeep;

    private ErrorAlarm(ErrorPolicySettings policy, Func<Task>? picoBeep)
    {
        _picoBeep = picoBeep;
        _loop = Task.Run(async () =>
        {
            var until = policy.AlarmDurationSeconds > 0 ? DateTimeOffset.UtcNow.AddSeconds(policy.AlarmDurationSeconds) : DateTimeOffset.MaxValue;
            do
            {
                if (policy.AlarmSource is "pc" or "both")
                {
                    try { Console.Beep(880, 180); } catch { }
                }
                if (policy.AlarmSource is "pico" or "both" && _picoBeep is not null)
                {
                    try { await _picoBeep(); } catch { }
                }
                if (!policy.RepeatAlarm) break;
                await Task.Delay(850, _cts.Token);
            } while (DateTimeOffset.UtcNow < until && !_cts.IsCancellationRequested);
        }, _cts.Token);
    }

    public static ErrorAlarm? Start(ErrorPolicySettings policy, Func<Task>? picoBeep = null, bool force = false)
    {
        if (!force && !policy.FatalAlarmEnabled) return null;
        bool pc = policy.AlarmSource is "pc" or "both";
        bool pico = policy.AlarmSource is "pico" or "both" && picoBeep is not null;
        return pc || pico ? new ErrorAlarm(policy, picoBeep) : null;
    }

    public void Dispose()
    {
        if (_cts.IsCancellationRequested) return;
        _cts.Cancel();
        try { _loop.Wait(250); } catch { }
        _cts.Dispose();
    }
}
