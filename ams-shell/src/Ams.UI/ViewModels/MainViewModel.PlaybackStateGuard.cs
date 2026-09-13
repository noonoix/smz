using System.ComponentModel;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private bool _playbackStateGuardInstalled;
    private bool _restoringPlaybackState;

    /// <summary>
    /// Stop cancels immediately, but the engine remains active until its finally block has sent
    /// HALT and released held input. Keep IsRunning true during that short unwind so the paired
    /// Run/Stop hotkey continues to mean Stop instead of attempting a new overlapping Run.
    /// </summary>
    public void InstallPlaybackStateGuard()
    {
        if (_playbackStateGuardInstalled) return;
        _playbackStateGuardInstalled = true;
        PropertyChanged += PreserveRunningStateUntilCleanup;
    }

    private void PreserveRunningStateUntilCleanup(object? sender, PropertyChangedEventArgs e)
    {
        if (_restoringPlaybackState || e.PropertyName != nameof(IsRunning) || IsRunning || !_runActive)
            return;

        _restoringPlaybackState = true;
        try
        {
            IsRunning = true;
            Log("stop acknowledged — Run remains locked until HALT/input cleanup completes");
        }
        finally
        {
            _restoringPlaybackState = false;
        }
    }
}
