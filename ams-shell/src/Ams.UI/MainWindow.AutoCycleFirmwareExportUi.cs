using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

internal static class AutoCycleFirmwareExportUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "AutoCycleFirmwareExportUiInstalled", typeof(bool), typeof(AutoCycleFirmwareExportUiBootstrap), new PropertyMetadata(false));

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
            Content = "خروجی Firmware چرخه‌ی خودکار برای Pico…",
            Padding = new Thickness(10, 5, 10, 5),
            Margin = new Thickness(0, 6, 0, 0),
            HorizontalAlignment = HorizontalAlignment.Stretch,
        };
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportAutoCyclePicoFirmwareCommand)));
        body.Children.Add(button);
    }
}
