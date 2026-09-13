using System.Windows;

namespace Ams.UI;

public partial class App : System.Windows.Application
{
    // v0.9.51 — elevated headless mode: the COM-history cleanup runs as a one-off
    // "--com-cleanup <request.json>" relaunch (Verb=runas) so the app itself never needs admin.
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args.Length > 0 && e.Args[0] == Services.BoardCleanupService.CleanupArg)
        {
            Shutdown(Services.BoardCleanupService.RunElevatedFromRequest(e.Args.Length > 1 ? e.Args[1] : null));
            return;
        }
        Services.ErrorPolicyBootstrap.Initialize();
        base.OnStartup(e);
    }
}
