using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Legacy separate plan export is intentionally hidden: the combined Guard bundle is the only board export.</summary>
internal static class AutoCycleExportUiBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        // Deliberately no UI hook. AutoCycle, macro routes and Guard must be exported atomically
        // by the single Combined Guard Bundle action.
    }
}
