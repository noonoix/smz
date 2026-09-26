using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

internal static class AutoCycleExportUiBootstrap
{
    // Legacy command marker retained for downstream contract readers: ExportAutoCyclePicoPlanCommand.
    // چرخهی خودکار / چرخه‌ی خودکار
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

        var panel = AutoCycleUiKit.EnsureExportCard(body);
        // One authoritative action: current tabs + modern low-memory runtime.
        // The Golden-100 command remains available to CI/legacy recovery but is not a
        // user-facing exporter because it intentionally contains a frozen sample project.
        var button = AutoCycleUiKit.Action("ساخت و کپی کامل پروژهٔ فعلی به درایو Pico", true);
        button.Tag = AutoCycleUiKit.PlanStepTag;
        button.ToolTip = "تمام تب‌های پروژهٔ باز را به Route تبدیل می‌کند، Bundle مدرن را می‌سازد و code.py را در آخر روی CIRCUITPY کپی می‌کند.";
        button.SetBinding(Button.CommandProperty,
            new Binding(nameof(MainViewModel.ExportAutoCycleModernCommand)));
        panel.Children.Add(button);
        AutoCycleUiKit.ReorderExportSteps(panel);
        AutoCycleUiKit.Reorder(body);
    }
}
