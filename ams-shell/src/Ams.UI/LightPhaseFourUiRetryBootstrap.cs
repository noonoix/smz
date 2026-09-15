using System.Reflection;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Orders the phase-four dynamic sections after the phase-three Status surface.
/// The Status panel starts collapsed, so its descendant visual tree may not exist
/// during MainWindow.Loaded. Keep a lightweight layout hook until Status is shown.
/// </summary>
internal static class LightPhaseFourUiRetryBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.DataContext is not MainViewModel vm) return;

        EventHandler? layoutHandler = null;
        layoutHandler = (_, _) =>
        {
            if (!ContainsText(window, "وضعیت زنده‌ی سنسور نور")) return;
            EnsureInstalled(window, vm);
            if (ContainsText(window, "تشخیص وضعیت نور")
                && ContainsText(window, "کالیبراسیون پیشنهادی"))
                window.LayoutUpdated -= layoutHandler;
        };
        window.LayoutUpdated += layoutHandler;

        window.Dispatcher.BeginInvoke(new Action(() => EnsureInstalled(window, vm)),
            DispatcherPriority.ContextIdle);
    }

    private static void EnsureInstalled(MainWindow window, MainViewModel vm)
    {
        if (!ContainsText(window, "وضعیت زنده‌ی سنسور نور")) return;
        if (!ContainsText(window, "تشخیص وضعیت نور"))
            InvokeInstaller(typeof(LightStateProfilesUiBootstrap), window, vm);
        if (!ContainsText(window, "کالیبراسیون پیشنهادی"))
            InvokeInstaller(typeof(LightCalibrationUiBootstrap), window, vm);
    }

    private static void InvokeInstaller(Type type, MainWindow window, MainViewModel vm)
    {
        try
        {
            type.GetMethod("Install", BindingFlags.Static | BindingFlags.NonPublic)?
                .Invoke(null, new object[] { window, vm });
        }
        catch
        {
            // Preserve the existing Status surface if an optional phase-four
            // installer fails; CI and hardware QA cover the added sections.
        }
    }

    private static bool ContainsText(DependencyObject root, string text)
    {
        if (root is TextBlock block && block.Text == text) return true;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            if (ContainsText(VisualTreeHelper.GetChild(root, i), text)) return true;
        return false;
    }
}
