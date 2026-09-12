using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;
using WpfBinding = System.Windows.Data.Binding;
using WpfTextBox = System.Windows.Controls.TextBox;

namespace Ams.UI;

/// <summary>Compact, accessible AutoCycle schedule card for the Play Options panel.</summary>
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

        var section = new StackPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Stretch,
        };
        var head = new Grid();
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var title = AutoCycleUiKit.Title("زمان‌بندی چرخه‌ی خودکار پیکو");
        var status = AutoCycleUiKit.Badge("Restart + Auto Resume");
        Grid.SetColumn(title, 0);
        Grid.SetColumn(status, 1);
        head.Children.Add(title);
        head.Children.Add(status);
        section.Children.Add(head);
        section.Children.Add(AutoCycleUiKit.Helper(
            "بازه‌های زمانی در هر چرخه دوباره قرعه‌کشی می‌شوند. Stop یا خطا هرگز Auto Resume را مسلح نمی‌کند."));

        var ranges = new Grid { Margin = new Thickness(0, 0, 0, 10) };
        ranges.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        ranges.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) });
        ranges.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        var restartRange = BuildRangeRow(
            "Restart پس از Start",
            nameof(MainViewModel.RestartMinMinutes), nameof(MainViewModel.RestartMaxMinutes),
            "کل برنامه در یک زمان تصادفی داخل این بازه متوقف و ویندوز Restart می‌شود.");
        var resumeRange = BuildRangeRow(
            "انتظار پس از آماده‌شدن USB/HID",
            nameof(MainViewModel.AutoResumeMinMinutes), nameof(MainViewModel.AutoResumeMaxMinutes),
            "پس از reconnect پایدار، یک زمان تازه از این بازه انتخاب می‌شود؛ سپس Resume Essentials اجرا می‌شود.");
        Grid.SetColumn(restartRange, 0);
        Grid.SetColumn(resumeRange, 2);
        ranges.Children.Add(restartRange);
        ranges.Children.Add(resumeRange);
        section.Children.Add(ranges);

        var resumeSurface = new Border
        {
            Background = AutoCycleUiKit.Raised,
            BorderBrush = AutoCycleUiKit.BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(12, 8, 12, 8),
        };
        var resumeEnabled = new CheckBox
        {
            Content = "شروع خودکار چرخه پس از Restart طبیعی",
            MinHeight = 40,
            VerticalContentAlignment = VerticalAlignment.Center,
            ToolTip = "فقط Restart طبیعی همین چرخه AUTO_RESUME_ARMED را فعال می‌کند؛ Stop یا خطا آن را فعال نمی‌کند.",
        };
        resumeEnabled.SetBinding(ToggleButton.IsCheckedProperty, TwoWay(nameof(MainViewModel.AutoResumeEnabled)));
        resumeSurface.Child = resumeEnabled;
        section.Children.Add(resumeSurface);

        var hardware = new Grid { Margin = new Thickness(0, 12, 0, 0) };
        hardware.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        hardware.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var hardwareText = new StackPanel();
        hardwareText.Children.Add(new TextBlock
        {
            Text = "خروجی صوتی پرتابل",
            Foreground = AutoCycleUiKit.Text,
            FontWeight = FontWeights.SemiBold,
        });
        hardwareText.Children.Add(new TextBlock
        {
            Text = "پایه‌ی ثابت سخت‌افزار؛ قابل ویرایش نیست",
            Foreground = AutoCycleUiKit.Muted,
            FontSize = 11,
            Margin = new Thickness(0, 3, 0, 0),
        });
        var buzzerValue = new TextBlock
        {
            FontFamily = new FontFamily("Cascadia Code"),
            FontWeight = FontWeights.SemiBold,
            Foreground = AutoCycleUiKit.Success,
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = "این مقدار سخت‌افزاری ثابت است و قابل تغییر نیست.",
        };
        buzzerValue.SetBinding(TextBlock.TextProperty, new WpfBinding(nameof(MainViewModel.PortableBuzzerPinText)));
        var buzzerBadge = new Border
        {
            Background = AutoCycleUiKit.Raised,
            BorderBrush = AutoCycleUiKit.BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(7),
            Padding = new Thickness(12, 7, 12, 7),
            Child = buzzerValue,
        };
        Grid.SetColumn(hardwareText, 0);
        Grid.SetColumn(buzzerBadge, 1);
        hardware.Children.Add(hardwareText);
        hardware.Children.Add(buzzerBadge);
        section.Children.Add(hardware);

        var help = new TextBlock
        {
            Margin = new Thickness(0, 12, 0, 0),
            Padding = new Thickness(12, 9, 12, 9),
            FontSize = 11,
            Foreground = AutoCycleUiKit.Muted,
            Background = AutoCycleUiKit.PrimarySoft,
            TextWrapping = TextWrapping.Wrap,
        };
        help.SetBinding(TextBlock.TextProperty, new WpfBinding(nameof(MainViewModel.AutoCycleHelpText)));
        section.Children.Add(help);

        body.Children.Add(AutoCycleUiKit.Card(AutoCycleUiKit.ScheduleTag, section));
        AutoCycleUiKit.Reorder(body);
    }

    private static FrameworkElement BuildRangeRow(
        string label, string minProperty, string maxProperty, string toolTip)
    {
        var root = new Border
        {
            Background = AutoCycleUiKit.Raised,
            BorderBrush = AutoCycleUiKit.BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(12),
            ToolTip = toolTip,
        };
        var stack = new StackPanel();
        stack.Children.Add(new TextBlock
        {
            Text = label + "  (دقیقه)",
            Foreground = AutoCycleUiKit.Text,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 0, 0, 9),
        });
        var row = new Grid();
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(20) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var minLabel = new TextBlock { Text = "حداقل", Foreground = AutoCycleUiKit.Muted, VerticalAlignment = VerticalAlignment.Center };
        var min = NumberBox(minProperty);
        var maxLabel = new TextBlock { Text = "حداکثر", Foreground = AutoCycleUiKit.Muted, VerticalAlignment = VerticalAlignment.Center };
        var max = NumberBox(maxProperty);
        Grid.SetColumn(minLabel, 0); Grid.SetColumn(min, 2); Grid.SetColumn(maxLabel, 4); Grid.SetColumn(max, 6);
        row.Children.Add(minLabel); row.Children.Add(min); row.Children.Add(maxLabel); row.Children.Add(max);
        stack.Children.Add(row);
        root.Child = stack;
        return root;
    }

    private static WpfTextBox NumberBox(string property)
    {
        var box = new WpfTextBox
        {
            Width = 64,
            MinHeight = 40,
            Padding = new Thickness(6, 4, 6, 4),
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
