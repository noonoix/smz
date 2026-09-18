using System.Runtime.CompilerServices;

namespace Ams.UI;

/// <summary>v32 uses the single Combined Guard Bundle action for all board output.</summary>
internal static class AutoCycleExportUiBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        // Intentionally no hook: separate plan export would create a second source of truth.
    }
}
