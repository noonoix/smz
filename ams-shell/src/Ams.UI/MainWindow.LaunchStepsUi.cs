using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Launch Steps selector shared by initial start and Auto Resume.</summary>
internal static class LaunchStepsUiBootstrap
{
    private const string CardTag = "AutoCycle.LaunchSteps";
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LaunchStepsUiInstalled", typeof(bool), typeof(LaunchStepsUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.FindName("PlayOptBody") is not StackPanel body) return;
        window.SetValue(InstalledProperty, true);

        var advanced = AutoCycleUiKit.EnsureAdvancedPanel(body);
        var root = new StackPanel { FlowDirection = FlowDirection.RightToLeft };
        root.Children.Add(AutoCycleUiKit.Title("Launch Steps — مشترک برای شروع و Resume"));
        root.Children.Add(AutoCycleUiKit.Helper(
            "یک For Loop را به‌عنوان گروه انتخاب کن؛ فرزندانش بعد از تأخیر تصادفی و Win+slot، فقط یک‌بار و به‌ترتیب اجرا می‌شوند و داخل Main Steps تکرار نمی‌شوند."));

        var status = new TextBlock
        {
            Foreground = AutoCycleUiKit.Muted,
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 6),
        };
        status.SetBinding(TextBlock.TextProperty, new Binding(nameof(MainViewModel.LaunchStepsStatus)));
        root.Children.Add(status);

        var actions = new WrapPanel { FlowDirection = FlowDirection.RightToLeft, HorizontalAlignment = HorizontalAlignment.Right };
        var mark = AutoCycleUiKit.Action("ثبت گروه Launch Steps", true);
        mark.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.MarkLaunchStepsCommand)));
        var clear = AutoCycleUiKit.Action("پاک‌کردن");
        clear.MinWidth = 110;
        clear.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.ClearLaunchStepsCommand)));
        actions.Children.Add(mark);
        actions.Children.Add(clear);
        root.Children.Add(actions);

        advanced.Children.Add(AutoCycleUiKit.Card(CardTag, root));
        AutoCycleUiKit.ReorderAdvanced(advanced);
        AutoCycleUiKit.Reorder(body);
    }
}
