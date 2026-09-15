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
/// Module/class-handler order is not guaranteed; hardware QA showed the original
/// one-shot installers could run before the Status body existed and then never retry.
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

        window.Dispatcher.BeginInvoke(new Action(async () =>
        {
            for (var attempt = 0; attempt < 12; attempt++)
            {
                if (ContainsText(window, "وضعیت زنده‌ی سنسور نور"))
                {
                    if (!ContainsText(window, "تشخیص وضعیت نور"))
                        InvokeInstaller(typeof(LightStateProfilesUiBootstrap), window, vm);
                    if (!ContainsText(window, "کالیبراسیون پیشنهادی"))
                        InvokeInstaller(typeof(LightCalibrationUiBootstrap), window, vm);
                    return;
                }
                await Task.Delay(100);
            }
        }), DispatcherPriority.ApplicationIdle);
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
            // Existing sections remain usable; the next test build exposes any
            // installer regression without taking down the application.
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
