using System.Runtime.CompilerServices;

namespace Ams.UI;

/// <summary>v32 exposes firmware only through the complete Combined Guard Bundle.</summary>
internal static class AutoCycleFirmwareExportUiBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        // Intentionally no hook: firmware-only export could overwrite the combined plan.
    }
}
