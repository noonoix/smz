using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// v0.9.67 — adds the portable automatic-cycle section to the existing Play Options body.
/// Kept in a partial file so the large main XAML stays stable while this feature is reviewed.
/// </summary>
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

        body.Children.Add(new Separator { Margin = new Thickness(0, 10, 0, 8) });

        var section = new StackPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Stretch,
        };
        body.Children.Add(section);

        section.Children.Add(new TextBlock
        {
            Text = "چرخه‌ی خودکار پیکو",
            FontWeight = FontWeights.SemiBold,
            FontSize = 13,
            Margin = new Thickness(0, 0, 0, 7),
        });

        section.Children.Add(BuildRangeRow(
            "Restart از لحظه‌ی Start (دقیقه)",
            nameof(MainViewModel.RestartMinMinutes), nameof(MainViewModel.RestartMaxMinutes),
            "کل برنامه در یک زمان تصادفی داخل این بازه متوقف و ویندوز Restart می‌شود."));

        var resumeEnabled = new CheckBox
        {
            Content = "شروع خودکار چرخه پس از Restart طبیعی",
            Margin = new Thickness(0, 7, 0, 5),
            VerticalContentAlignment = VerticalAlignment.Center,
            ToolTip = "فقط Restart طبیعی همین چرخه AUTO_RESUME_ARMED را فعال می‌کند؛ Stop یا خطا آن را فعال نمی‌کند.",
        };
        resumeEnabled.SetBinding(ToggleButton.IsCheckedProperty, TwoWay(nameof(MainViewModel.AutoResumeEnabled)));
        section.Children.Add(resumeEnabled);

        section.Children.Add(BuildRangeRow(
            "انتظار پس از آماده‌شدن USB/HID (دقیقه)",
            nameof(MainViewModel.AutoResumeMinMinutes), nameof(MainViewModel.AutoResumeMaxMinutes),
            "پس از reconnect پایدار، یک زمان تازه از این بازه انتخاب می‌شود؛ سپس Resume Essentials اجرا می‌شود."));

        var buzzer = new Grid { Margin = new Thickness(0, 7, 0, 0) };
        buzzer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(210) });
        buzzer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var buzzerLabel = new TextBlock
        {
            Text = "پایه‌ی بازر پرتابل",
            VerticalAlignment = VerticalAlignment.Center,
        };
        var buzzerValue = new TextBlock
        {
            FontFamily = new FontFamily("Cascadia Code"),
            FontWeight = FontWeights.SemiBold,
            VerticalAlignment = VerticalAlignment.Center,
            ToolTip = "این مقدار سخت‌افزاری ثابت است و قابل تغییر نیست.",
        };
        buzzerValue.SetBinding(TextBlock.TextProperty, new Binding(nameof(MainViewModel.PortableBuzzerPinText)));
        Grid.SetColumn(buzzerLabel, 0);
        Grid.SetColumn(buzzerValue, 1);
        buzzer.Children.Add(buzzerLabel);
        buzzer.Children.Add(buzzerValue);
        section.Children.Add(buzzer);

        var help = new TextBlock
        {
            Margin = new Thickness(0, 7, 0, 0),
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Opacity = 0.78,
        };
        help.SetBinding(TextBlock.TextProperty, new Binding(nameof(MainViewModel.AutoCycleHelpText)));
        section.Children.Add(help);
    }

    private static FrameworkElement BuildRangeRow(
        string label, string minProperty, string maxProperty, string toolTip)
    {
        var root = new StackPanel { Margin = new Thickness(0, 3, 0, 2), ToolTip = toolTip };
        root.Children.Add(new TextBlock { Text = label, Margin = new Thickness(0, 0, 0, 3) });

        var row = new StackPanel { Orientation = Orientation.Horizontal };
        row.Children.Add(new TextBlock
        {
            Text = "حداقل",
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 5, 0),
        });
        row.Children.Add(NumberBox(minProperty));
        row.Children.Add(new TextBlock
        {
            Text = "حداکثر",
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(14, 0, 5, 0),
        });
        row.Children.Add(NumberBox(maxProperty));
        root.Children.Add(row);
        return root;
    }

    private static TextBox NumberBox(string property)
    {
        var box = new TextBox
        {
            Width = 58,
            Padding = new Thickness(4, 2, 4, 2),
            TextAlignment = TextAlignment.Center,
            VerticalContentAlignment = VerticalAlignment.Center,
            FlowDirection = FlowDirection.LeftToRight,
        };
        box.SetBinding(TextBox.TextProperty, new Binding(property)
        {
            Mode = BindingMode.TwoWay,
            UpdateSourceTrigger = UpdateSourceTrigger.LostFocus,
            ValidatesOnExceptions = true,
        });
        return box;
    }

    private static Binding TwoWay(string property) => new(property)
    {
        Mode = BindingMode.TwoWay,
        UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged,
    };
}
