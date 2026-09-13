using System.Windows;

namespace Ams.UI.Services;

/// <summary>Installs process-level safety nets early. Normal Stop, Pause, completion and
/// OperationCanceledException are intentionally not routed here as fatal errors.</summary>
public static class ErrorPolicyBootstrap
{
    private static readonly object Gate = new();
    private static ErrorAlarm? _alarm;
    private static bool _installed;

    public static ErrorPolicySettings Settings { get; private set; } = ErrorPolicySettings.Load();

    public static void Initialize()
    {
        lock (Gate)
        {
            if (_installed) return;
            _installed = true;
            Settings = ErrorPolicySettings.Load();
            System.Windows.Application.Current.DispatcherUnhandledException += (_, e) =>
            {
                if (Handle(e.Exception, "ui")) e.Handled = true;
            };
            TaskScheduler.UnobservedTaskException += (_, e) =>
            {
                Handle(e.Exception, "task");
                e.SetObserved();
            };
            AppDomain.CurrentDomain.UnhandledException += (_, e) =>
                Handle(e.ExceptionObject as Exception ?? new Exception(e.ExceptionObject?.ToString()), "process");
        }
    }

    public static bool Handle(Exception error, string source, string? tab = null)
    {
        if (error is OperationCanceledException || error is RunEngine.SilentStop || error is RunEngine.PolicyStop) return false;
        lock (Gate)
        {
            Settings.Record(source, error, tab);
            if (!Settings.FatalAlarmEnabled) return false;
            _alarm?.Dispose();
            _alarm = ErrorAlarm.Start(Settings);
            return true;
        }
    }

    public static void Acknowledge()
    {
        lock (Gate) { _alarm?.Dispose(); _alarm = null; }
    }
}
