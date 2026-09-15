using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Binds the existing Status readiness card to read-only gate diagnostics.</summary>
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
        window.Dispatcher.BeginInvoke(new Action(() => Install(window, vm)),
            System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static void Install(MainWindow window, MainViewModel vm)
    {
        var readiness = FindText(window, "فقط تشخیصی · گیت اجرایی خاموش است");
        if (readiness is not null)
        {
            readiness.SetBinding(TextBlock.TextProperty,
                new Binding(nameof(MainViewModel.LightGateDiagnosticDisplay)));
            readiness.SetBinding(FrameworkElement.ToolTipProperty,
                new Binding(nameof(MainViewModel.LightGateDiagnosticReasonDisplay)));
        }

        vm.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName != nameof(MainViewModel.IsLightWatchRunning)) return;
            if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
            else vm.StopLightGateDiagnosticSession();
        };

        if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
        else vm.StopLightGateDiagnosticSession();
    }

    private static TextBlock? FindText(DependencyObject root, string text)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is TextBlock block && block.Text == text) return block;
            var found = FindText(child, text);
            if (found is not null) return found;
        }
        return null;
    }
}
