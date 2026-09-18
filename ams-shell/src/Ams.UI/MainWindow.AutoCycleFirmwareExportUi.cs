using System.Runtime.CompilerServices;

namespace Ams.UI;

/// <summary>Legacy firmware-only export is hidden to prevent split plan/runtime bundles.</summary>
internal static class AutoCycleFirmwareExportUiBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        // Deliberately no UI hook. The combined Guard bundle owns the complete board payload.
    }
}
