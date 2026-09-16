using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Dedicated Classroom Studio action for the combined Pico + Arduino portable bundle.</summary>
internal static class CombinedGuardExportUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "CombinedGuardExportUiInstalled", typeof(bool), typeof(CombinedGuardExportUiBootstrap), new PropertyMetadata(false));

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
        var button = AutoCycleUiKit.Action("۰  ·  ساخت Combined Guard Bundle", true);
        button.ToolTip = "بسته‌ی کامل Pico + Arduino arm: plan.txt با STATELOOP، هفت route، manifest، calibration و runtimeهای CIRCUITPY.";
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportCombinedPortableGuardCommand)));
        panel.Children.Insert(0, button);
        AutoCycleUiKit.Reorder(body);
    }
}
