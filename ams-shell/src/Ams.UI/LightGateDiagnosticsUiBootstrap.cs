using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Binds the existing Status readiness card to read-only gate diagnostics. Lifecycle tracking is
/// installed immediately; visual binding retries until the initially collapsed Status tree exists.
/// </summary>
internal static class LightGateDiagnosticsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LightGateDiagnosticsInstalled", typeof(bool), typeof(LightGateDiagnosticsUiBootstrap),
        new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window
            || window.GetValue(InstalledProperty) is true
            || window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);

        vm.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName != nameof(MainViewModel.IsLightWatchRunning)) return;
            if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
            else vm.StopLightGateDiagnosticSession();
        };
        if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
        else vm.StopLightGateDiagnosticSession();

        EventHandler? layoutHandler = null;
        layoutHandler = (_, _) =>
        {
            if (!TryBind(window, vm)) return;
            window.LayoutUpdated -= layoutHandler;
        };
        window.LayoutUpdated += layoutHandler;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            if (TryBind(window, vm)) window.LayoutUpdated -= layoutHandler;
        }), System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static bool TryBind(MainWindow window, MainViewModel vm)
    {
        var readiness = FindText(window, "فقط تشخیصی · گیت اجرایی خاموش است");
        if (readiness is null) return false;
        readiness.SetBinding(TextBlock.TextProperty,
            new Binding(nameof(MainViewModel.LightGateDiagnosticDisplay)) { Source = vm });
        readiness.SetBinding(FrameworkElement.ToolTipProperty,
            new Binding(nameof(MainViewModel.LightGateDiagnosticReasonDisplay)) { Source = vm });
        return true;
    }

    private static TextBlock? FindText(DependencyObject root, string text)
    {
        if (root is TextBlock rootBlock && rootBlock.Text == text) return rootBlock;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var found = FindText(VisualTreeHelper.GetChild(root, i), text);
            if (found is not null) return found;
        }
        return null;
    }
}
