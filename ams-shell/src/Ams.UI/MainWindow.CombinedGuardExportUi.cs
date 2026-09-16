using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Dedicated Classroom Studio action for the combined Pico + Arduino portable bundle.</summary>
internal static class CombinedGuardExportUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "CombinedGuardExportUiInstalled", typeof(bool), typeof(CombinedGuardExportUiBootstrap), new PropertyMetadata(false));
    private static readonly DependencyProperty RetryHookInstalledProperty = DependencyProperty.RegisterAttached(
        "CombinedGuardExportUiRetryHookInstalled", typeof(bool), typeof(CombinedGuardExportUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (TryInstall(window)) return;
        if (window.GetValue(RetryHookInstalledProperty) is true) return;
        window.SetValue(RetryHookInstalledProperty, true);

        EventHandler? layoutHandler = null;
        layoutHandler = (_, _) =>
        {
            if (!TryInstall(window)) return;
            window.LayoutUpdated -= layoutHandler;
        };
        window.LayoutUpdated += layoutHandler;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            if (TryInstall(window)) window.LayoutUpdated -= layoutHandler;
        }), System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static bool TryInstall(MainWindow window)
    {
        if (FindNamedStackPanel(window, "PlayOptBody") is not StackPanel body) return false;
        window.SetValue(InstalledProperty, true);

        var panel = AutoCycleUiKit.EnsureExportCard(body);
        var button = AutoCycleUiKit.Action("۰  ·  ساخت Combined Guard Bundle", true);
        button.ToolTip = "بسته‌ی کامل Pico + Arduino arm: plan.txt با STATELOOP، هفت route، manifest، calibration و runtimeهای CIRCUITPY.";
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportCombinedPortableGuardCommand)));
        panel.Children.Insert(0, button);
        AutoCycleUiKit.Reorder(body);
        return true;
    }

    private static StackPanel? FindNamedStackPanel(DependencyObject root, string name)
    {
        if (root is FrameworkElement element && element.Name == name && root is StackPanel panel) return panel;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var found = FindNamedStackPanel(VisualTreeHelper.GetChild(root, i), name);
            if (found is not null) return found;
        }
        return null;
    }
}
