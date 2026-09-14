using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;
using WpfBinding = System.Windows.Data.Binding;
using WpfTextBox = System.Windows.Controls.TextBox;
using WpfPanel = System.Windows.Controls.Panel;

namespace Ams.UI;

/// <summary>Space-efficient AutoCycle schedule kept inside collapsed advanced settings.</summary>
public partial class MainWindow
{
    private static readonly DependencyProperty AutoCycleUiInstalledProperty =
        DependencyProperty.RegisterAttached(
            "AutoCycleUiInstalled", typeof(bool), typeof(MainWindow), new PropertyMetadata(false));

    static MainWindow()
    {
        EventManager.RegisterClassHandler(
            typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(InstallAutoCycleUi), true);
    }

    private static void InstallAutoCycleUi(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(AutoCycleUiInstalledProperty) is true) return;
        if (window.FindName("PlayOptBody") is not StackPanel body) return;
        window.SetValue(AutoCycleUiInstalledProperty, true);

        var advanced = AutoCycleUiKit.EnsureAdvancedPanel(body);
        MovePlayOptionsToInspector(window, body);
        var section = new StackPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Stretch,
        };

        var head = new Grid { Margin = new Thickness(0, 0, 0, 6) };
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var title = AutoCycleUiKit.Title("زمان‌بندی چرخه‌ی خودکار پیکو");
        var buzzerValue = new TextBlock
        {
            Foreground = AutoCycleUiKit.Success,
            FontSize = 10,
            FontWeight = FontWeights.SemiBold,
            VerticalAlignment = VerticalAlignment.Center,
        };
        buzzerValue.SetBinding(TextBlock.TextProperty,
            new WpfBinding(nameof(MainViewModel.PortableBuzzerPinText)));
        var status = new Border
        {
            Background = AutoCycleUiKit.Raised,
            CornerRadius = new CornerRadius(5),
            Padding = new Thickness(7, 2, 7, 2),
            ToolTip = "پایه‌ی ثابت خروجی صوتی پرتابل",
            Child = buzzerValue,
        };
        Grid.SetColumn(title, 0);
        Grid.SetColumn(status, 1);
        head.Children.Add(title);
        head.Children.Add(status);
        section.Children.Add(head);

        var ranges = new WrapPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Right,
        };
        ranges.Children.Add(BuildRangeRow(
            "Restart از Start", "دقیقه",
            nameof(MainViewModel.RestartMinMinutes), nameof(MainViewModel.RestartMaxMinutes),
            "کل برنامه در یک زمان تصادفی داخل این بازه متوقف و ویندوز Restart می‌شود."));
        ranges.Children.Add(BuildRangeRow(
            "USB/HID تا Resume", "دقیقه",
            nameof(MainViewModel.AutoResumeMinMinutes), nameof(MainViewModel.AutoResumeMaxMinutes),
            "پس از reconnect پایدار، یک زمان تازه از این بازه انتخاب می‌شود؛ سپس Resume Essentials اجرا می‌شود."));
        section.Children.Add(ranges);

        var launch = new WrapPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(0, 6, 0, 0),
        };
        var launchEnabled = new CheckBox
        {
            Content = "Restart Launch",
            MinHeight = 32,
            VerticalContentAlignment = VerticalAlignment.Center,
            ToolTip = "پس از بازگشت Windows و پیش از Resume Essentials، برنامه‌ی پین‌شده را با Win+شماره اجرا می‌کند.",
            Margin = new Thickness(8, 0, 0, 0),
        };
        launchEnabled.SetBinding(ToggleButton.IsCheckedProperty,
            TwoWay(nameof(MainViewModel.PostRestartLaunchEnabled)));
        launch.Children.Add(launchEnabled);
        launch.Children.Add(new TextBlock
        {
            Text = "جایگاه Taskbar",
            Foreground = AutoCycleUiKit.Muted,
            FontSize = 10,
            VerticalAlignment = VerticalAlignment.Center,
        });
        launch.Children.Add(NumberBox(nameof(MainViewModel.PostRestartTaskbarSlot)));
        launch.Children.Add(BuildRangeRow(
            "مکث قبل", "ثانیه",
            nameof(MainViewModel.PostRestartLaunchBeforeMinSeconds),
            nameof(MainViewModel.PostRestartLaunchBeforeMaxSeconds),
            "مکث تصادفی پیش از Win+شماره."));
        launch.Children.Add(BuildRangeRow(
            "مکث بعد", "ثانیه",
            nameof(MainViewModel.PostRestartLaunchAfterMinSeconds),
            nameof(MainViewModel.PostRestartLaunchAfterMaxSeconds),
            "فرصت تصادفی برای بازشدن برنامه پیش از Resume Essentials."));
        section.Children.Add(launch);

        var footer = new Grid { Margin = new Thickness(0, 6, 0, 0) };
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var resumeEnabled = new CheckBox
        {
            Content = "شروع خودکار فقط پس از Restart طبیعی",
            MinHeight = 32,
            VerticalContentAlignment = VerticalAlignment.Center,
            ToolTip = "Stop یا خطا AUTO_RESUME_ARMED را فعال نمی‌کند.",
        };
        resumeEnabled.SetBinding(ToggleButton.IsCheckedProperty, TwoWay(nameof(MainViewModel.AutoResumeEnabled)));
        var help = new TextBlock
        {
            Foreground = AutoCycleUiKit.Muted,
            FontSize = 10,
            VerticalAlignment = VerticalAlignment.Center,
            TextTrimming = TextTrimming.CharacterEllipsis,
            MaxWidth = 520,
        };
        help.SetBinding(TextBlock.TextProperty, new WpfBinding(nameof(MainViewModel.AutoCycleHelpText)));
        help.SetBinding(ToolTipProperty, new WpfBinding(nameof(MainViewModel.AutoCycleHelpText)));
        Grid.SetColumn(help, 0);
        Grid.SetColumn(resumeEnabled, 1);
        footer.Children.Add(help);
        footer.Children.Add(resumeEnabled);
        section.Children.Add(footer);

        advanced.Children.Add(AutoCycleUiKit.Card(AutoCycleUiKit.ScheduleTag, section));
        AutoCycleUiKit.ReorderAdvanced(advanced);
        AutoCycleUiKit.Reorder(body);
    }

    private static void MovePlayOptionsToInspector(MainWindow window, StackPanel body)
    {
        if (window.FindName("InspectorExtras") is not StackPanel host) return;
        Border? owner = null;
        for (DependencyObject? p = body; p is not null; p = VisualTreeHelper.GetParent(p))
            if (p is Border border) { owner = border; break; }
        if (owner is null || owner.Parent is not WpfPanel oldParent || host.Children.Contains(owner)) return;
        oldParent.Children.Remove(owner);
        owner.Margin = new Thickness(0, 0, 0, 8);
        host.Children.Add(owner);
    }

    private static FrameworkElement BuildRangeRow(
        string label, string unit, string minProperty, string maxProperty, string toolTip)
    {
        var root = new Border
        {
            Background = AutoCycleUiKit.Raised,
            BorderBrush = AutoCycleUiKit.BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(8, 5, 8, 5),
            Margin = new Thickness(8, 0, 0, 0),
            ToolTip = toolTip,
        };
        var row = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            FlowDirection = FlowDirection.RightToLeft,
            VerticalAlignment = VerticalAlignment.Center,
        };
        row.Children.Add(new TextBlock
        {
            Text = label + " (" + unit + ")",
            Foreground = AutoCycleUiKit.Text,
            FontSize = 11,
            FontWeight = FontWeights.SemiBold,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(8, 0, 0, 0),
        });
        row.Children.Add(new TextBlock { Text = "حداقل", Foreground = AutoCycleUiKit.Muted, FontSize = 10, VerticalAlignment = VerticalAlignment.Center });
        row.Children.Add(NumberBox(minProperty));
        row.Children.Add(new TextBlock { Text = "حداکثر", Foreground = AutoCycleUiKit.Muted, FontSize = 10, VerticalAlignment = VerticalAlignment.Center });
        row.Children.Add(NumberBox(maxProperty));
        root.Child = row;
        return root;
    }

    private static WpfTextBox NumberBox(string property)
    {
        var box = new WpfTextBox
        {
            Width = 52,
            MinHeight = 32,
            Padding = new Thickness(5, 2, 5, 2),
            Margin = new Thickness(5, 0, 8, 0),
            TextAlignment = TextAlignment.Center,
            VerticalContentAlignment = VerticalAlignment.Center,
            FlowDirection = FlowDirection.LeftToRight,
        };
        box.SetBinding(WpfTextBox.TextProperty, new WpfBinding(property)
        {
            Mode = BindingMode.TwoWay,
            UpdateSourceTrigger = UpdateSourceTrigger.LostFocus,
            ValidatesOnExceptions = true,
        });
        return box;
    }

    private static WpfBinding TwoWay(string property) => new(property)
    {
        Mode = BindingMode.TwoWay,
        UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged,
    };
}
