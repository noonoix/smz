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

        var panel = AutoCycleUiKit.EnsureExportCard(body);
        var button = AutoCycleUiKit.Action("۲  ·  ساخت Firmware چرخه‌ی خودکار");
        button.Tag = AutoCycleUiKit.FirmwareStepTag;
        button.ToolTip = "code.py و runtimeهای firmware را می‌سازد؛ در همان پوشه‌ی مرحله‌ی ۱ ذخیره کن.";
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportAutoCyclePicoFirmwareCommand)));
        panel.Children.Add(button);
        AutoCycleUiKit.ReorderExportSteps(panel);
        AutoCycleUiKit.Reorder(body);
    }
}
