using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using WpfBrush = System.Windows.Media.Brush;
using WpfComboBox = System.Windows.Controls.ComboBox;

namespace Ams.UI.Views;

/// <summary>Behavior-tab controls for the shared fatal-error policy. Kept in a partial file so
/// older saved settings and the existing dialog layout remain source-compatible.</summary>
public partial class OptionsDialog
{
    private bool _errorPolicyUiAdded;

    protected override void OnContentRendered(EventArgs e)
    {
        base.OnContentRendered(e);
        if (_errorPolicyUiAdded) return;
        _errorPolicyUiAdded = true;
        AddErrorPolicyControls();
    }

    private void AddErrorPolicyControls()
    {
        var settings = Services.ErrorPolicyBootstrap.Settings;
        var panel = new StackPanel { Margin = new Thickness(0, 12, 0, 0) };
        panel.Children.Add(new Separator { Margin = new Thickness(0, 0, 0, 8) });
        panel.Children.Add(new TextBlock
        {
            Text = "مدیریت خطا — مشترک برای هر پنج تب",
            FontWeight = FontWeights.SemiBold,
            FontSize = 14,
            Foreground = (WpfBrush)FindResource("TextPrimaryBrush"),
            TextAlignment = TextAlignment.Right,
            Margin = new Thickness(0, 0, 0, 6)
        });

        var alarm = new CheckBox
        {
            Content = "در خطای جدی، هشدار تکرارشونده فعال شود",
            IsChecked = settings.FatalAlarmEnabled,
            Foreground = (WpfBrush)FindResource("TextPrimaryBrush"),
            FlowDirection = FlowDirection.RightToLeft
        };
        alarm.Checked += (_, _) => Update(s => s.FatalAlarmEnabled = true);
        alarm.Unchecked += (_, _) => { Update(s => s.FatalAlarmEnabled = false); Services.ErrorPolicyBootstrap.Acknowledge(); };
        panel.Children.Add(alarm);

        panel.Children.Add(new TextBlock { Text = "منبع هشدار", Foreground = (WpfBrush)FindResource("TextSecondaryBrush"), Margin = new Thickness(0, 8, 0, 2), TextAlignment = TextAlignment.Right });
        var source = new WpfComboBox { SelectedValuePath = "Tag", HorizontalContentAlignment = HorizontalAlignment.Right };
        source.Items.Add(new ComboBoxItem { Content = "پیکو + رایانه", Tag = "both" });
        source.Items.Add(new ComboBoxItem { Content = "فقط پیکو", Tag = "pico" });
        source.Items.Add(new ComboBoxItem { Content = "فقط رایانه", Tag = "pc" });
        source.SelectedValue = settings.AlarmSource;
        source.SelectionChanged += (_, _) => { if (source.SelectedValue is string v) Update(s => s.AlarmSource = v); };
        panel.Children.Add(source);

        var repeat = new CheckBox
        {
            Content = "تا Stop یا تأیید دستی ادامه پیدا کند",
            IsChecked = settings.RepeatAlarm,
            Foreground = (WpfBrush)FindResource("TextPrimaryBrush"),
            Margin = new Thickness(0, 8, 0, 0),
            FlowDirection = FlowDirection.RightToLeft
        };
        repeat.Checked += (_, _) => Update(s => s.RepeatAlarm = true);
        repeat.Unchecked += (_, _) => Update(s => s.RepeatAlarm = false);
        panel.Children.Add(repeat);

        panel.Children.Add(new TextBlock { Text = "رفتار Timeout استپ‌های دارای پنجره انتظار", Foreground = (WpfBrush)FindResource("TextSecondaryBrush"), Margin = new Thickness(0, 8, 0, 2), TextAlignment = TextAlignment.Right });
        var timeout = new WpfComboBox { SelectedValuePath = "Tag", HorizontalContentAlignment = HorizontalAlignment.Right };
        timeout.Items.Add(new ComboBoxItem { Content = "توقف + هشدار", Tag = "stopWithAlarm" });
        timeout.Items.Add(new ComboBoxItem { Content = "توقف بی‌صدا", Tag = "stopQuiet" });
        timeout.Items.Add(new ComboBoxItem { Content = "ادامه اجرا", Tag = "continue" });
        timeout.SelectedValue = settings.TimeoutPolicy;
        timeout.SelectionChanged += (_, _) => { if (timeout.SelectedValue is string v) Update(s => s.TimeoutPolicy = v); };
        panel.Children.Add(timeout);

        var row = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        var acknowledge = new Button { Content = "توقف هشدار فعلی", Padding = new Thickness(10, 3, 10, 3), Margin = new Thickness(0, 0, 6, 0) };
        acknowledge.Click += (_, _) => Services.ErrorPolicyBootstrap.Acknowledge();
        var clear = new Button { Content = "پاک‌کردن سابقه خطا", Padding = new Thickness(10, 3, 10, 3) };
        clear.Click += (_, _) => { settings.ErrorHistory.Clear(); settings.Save(); };
        row.Children.Add(acknowledge);
        row.Children.Add(clear);
        panel.Children.Add(row);

        panel.Children.Add(new TextBlock
        {
            Text = "تنظیمات برای Launch، Main، هر دو مسیر Recovery و Resume Essentials یکی است. Stop دستی و مکث خطای جدی محسوب نمی‌شوند.",
            TextWrapping = TextWrapping.Wrap,
            TextAlignment = TextAlignment.Right,
            FontSize = 11,
            Foreground = (WpfBrush)FindResource("TextTertiaryBrush"),
            Margin = new Thickness(0, 8, 0, 0)
        });
        BehaviorPanel.Children.Add(panel);

        void Update(Action<Services.ErrorPolicySettings> change)
        {
            change(settings);
            settings.Save();
        }
    }
}
