using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Compact Resume Essentials controls, hidden with advanced AutoCycle settings by default.</summary>
internal static class ResumeEssentialsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "ResumeEssentialsUiInstalled", typeof(bool), typeof(ResumeEssentialsUiBootstrap), new PropertyMetadata(false));

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
        var row = new Grid { FlowDirection = FlowDirection.RightToLeft };
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var text = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
        text.Children.Add(AutoCycleUiKit.Title("Resume Essentials"));
        text.Children.Add(AutoCycleUiKit.Helper(
            "Random Package انتخابی پس از Auto Resume یک‌بار در حالت Shuffle All اجرا می‌شود."));

        var actions = new WrapPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Center,
        };
        var mark = AutoCycleUiKit.Action("ثبت بسته", true);
        mark.ToolTip = "بسته‌ی انتخاب‌شده را به‌عنوان پیش‌اجرای یک‌باره ثبت می‌کند.";
        mark.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.MarkResumeEssentialsCommand)));
        var clear = AutoCycleUiKit.Action("پاک‌کردن");
        clear.MinWidth = 110;
        clear.ToolTip = "انتخاب Resume Essentials را پاک می‌کند.";
        clear.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.ClearResumeEssentialsCommand)));
        actions.Children.Add(mark);
        actions.Children.Add(clear);

        Grid.SetColumn(text, 0);
        Grid.SetColumn(actions, 1);
        row.Children.Add(text);
        row.Children.Add(actions);
        advanced.Children.Add(AutoCycleUiKit.Card(AutoCycleUiKit.EssentialsTag, row));
        AutoCycleUiKit.ReorderAdvanced(advanced);
        AutoCycleUiKit.Reorder(body);
    }
}
