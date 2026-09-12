using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Cycle-aware exporter button hosted with its own settings.</summary>
internal static class AutoCycleExportUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "AutoCycleExportUiInstalled", typeof(bool), typeof(AutoCycleExportUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.FindName("PlayOptBody") is not StackPanel body) return;
        window.SetValue(InstalledProperty, true);

        var button = new Button
        {
            Content = "۱) ساخت پلن چرخه‌ی خودکار (AutoCycle؛ جایگزین Export Pico Plan)…",
            ToolTip = "plan.txt و runtimeهای PLAN را برای AutoCycle می‌سازد؛ خروجی عادی پلن را در همان پوشه جایگزین می‌کند.",
            Padding = new Thickness(10, 5, 10, 5),
            Margin = new Thickness(0, 10, 0, 0),
            HorizontalAlignment = HorizontalAlignment.Stretch,
        };
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportAutoCyclePicoPlanCommand)));
        body.Children.Add(button);
    }
}
