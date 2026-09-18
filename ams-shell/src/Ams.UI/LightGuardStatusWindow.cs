using System.Windows;
using System.Windows.Controls;
using WpfControl = System.Windows.Controls.Control;
using System.Windows.Data;
using System.Windows.Media;
using WpfColor = System.Windows.Media.Color;
using WpfColorConverter = System.Windows.Media.ColorConverter;
using Ams.UI.ViewModels;

namespace Ams.UI;

internal static class LightGuardStatusWindow
{
    private static Window? _window;
    public static void Show(Window owner, MainViewModel vm)
    {
        if (_window is { IsVisible: true }) { _window.Activate(); return; }
        var stack = new StackPanel { Margin = new Thickness(18) };
        stack.Children.Add(Text("وضعیت Guard — Phase 7", 18, FontWeights.SemiBold));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardIdentityDisplay)));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardRevisionDisplay)));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardRevisionComparison), "#DE9255"));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardCalibrationStatus), "#72BC8F"));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardObservationStatus)));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardComparisonStatus), "#DE9255"));
        var comparison = new ItemsControl();
        comparison.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardComparisonDisplays)) { Source = vm });
        stack.Children.Add(comparison);
        var actions = new WrapPanel { Margin = new Thickness(0, 12, 0, 0) };
        actions.Children.Add(Action("دریافت از Pico", "#5E9FE8", () => vm.PullLightGuardCalibrationAsync()));
        actions.Children.Add(Action("مقایسه با Pico", "#B8893D", () => vm.CompareLightGuardCalibrationAsync()));
        actions.Children.Add(Action("ارسال به Pico", "#3D6B55", () => vm.SyncLightGuardCalibrationAsync()));
        actions.Children.Add(Action("CALGET", "#4B5563", () => vm.RefreshLightGuardIdentityAsync()));
        actions.Children.Add(Action("Guard OFF", "#333740", () => vm.DisableLightGuardAsync()));
        actions.Children.Add(Action("Guard ON", "#3D6B55", () => vm.EnableLightGuardAsync()));
        stack.Children.Add(actions);
        var profiles = new ItemsControl();
        profiles.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardProfileDisplays)) { Source = vm });
        stack.Children.Add(profiles);
        var tabs = new TabControl();
        tabs.Items.Add(new TabItem
        {
            Header = "وضعیت Guard",
            Content = new ScrollViewer { Content = stack, VerticalScrollBarVisibility = ScrollBarVisibility.Auto }
        });
        tabs.Items.Add(BuildCalibrationTab(vm));
        _window = new Window { Title = "Guard Status", Owner = owner, Width = 720, Height = 560, MinWidth = 560, MinHeight = 400, WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = Brush("#22262D"), Content = tabs };
        _window.Closed += (_, _) => _window = null; _window.Show();
    }

    private static TabItem BuildCalibrationTab(MainViewModel vm)
    {
        var panel = new StackPanel { Margin = new Thickness(18) };
        panel.Children.Add(Text("تنظیمات کالیبراسیون برد", 18, FontWeights.SemiBold));
        panel.Children.Add(Text("این مقادیر همراه Guard Bundle روی Pico قرار می‌گیرند و فقط روی کالیبراسیون‌های بعدی یا Reset اثر دارند.", 13, FontWeights.Normal, "#AAB3C2"));

        var tolerance = new TextBox { Text = vm.LightGuardDefaultTolerance.ToString("0.###"), Margin = new Thickness(3), MinWidth = 120 };
        var stable = new TextBox { Text = vm.LightGuardDefaultStableDurationMs.ToString(), Margin = new Thickness(3), MinWidth = 120 };
        var hysteresis = new TextBox { Text = vm.LightGuardDefaultHysteresisLux.ToString("0.###"), Margin = new Thickness(3), MinWidth = 120 };
        panel.Children.Add(Labeled("تلورانس پیش‌فرض", tolerance));
        panel.Children.Add(Labeled("پایداری پیش‌فرض (ms)", stable));
        panel.Children.Add(Labeled("Hysteresis پیش‌فرض (Lux)", hysteresis));
        panel.Children.Add(Text("مقادیر فعلی: تلورانس و Hysteresis برحسب Lux، پایداری برحسب میلی‌ثانیه.", 12, FontWeights.Normal, "#AAB3C2"));
        panel.Children.Add(Action("ذخیره تنظیمات کالیبراسیون", "#3D6B55", () =>
        {
            if (!double.TryParse(tolerance.Text, out var t) || t < 0
                || !int.TryParse(stable.Text, out var st) || st < 0
                || !double.TryParse(hysteresis.Text, out var h) || h < 0)
            {
                MessageBox.Show("مقادیر کالیبراسیون معتبر نیستند.", "Guard", MessageBoxButton.OK, MessageBoxImage.Warning);
                return Task.CompletedTask;
            }
            vm.LightGuardDefaultTolerance = t;
            vm.LightGuardDefaultStableDurationMs = st;
            vm.LightGuardDefaultHysteresisLux = h;
            vm.SaveLightGuardDefaults();
            return Task.CompletedTask;
        }));
        return new TabItem { Header = "کالیبراسیون", Content = new ScrollViewer { Content = panel, VerticalScrollBarVisibility = ScrollBarVisibility.Auto } };
    }

    private static StackPanel Labeled(string label, WpfControl input)
    {
        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 5, 0, 5) };
        row.Children.Add(Text(label, 13, FontWeights.Normal, "#D9DEE7"));
        row.Children.Add(input);
        return row;
    }

    private static Button Action(string label, string background, Func<Task> action)
    { var b = new Button { Content = label, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(4), Background = Brush(background), Foreground = Brush("#F5F7FA") }; b.Click += async (_, _) => await action(); return b; }
    private static TextBlock Bound(MainViewModel vm, string path, string color = "#D9DEE7") { var t = Text("", 13, FontWeights.Normal, color); t.SetBinding(TextBlock.TextProperty, new Binding(path) { Source = vm }); return t; }
    private static TextBlock Text(string value, double size, FontWeight weight, string color = "#F5F7FA") => new() { Text = value, FontSize = size, FontWeight = weight, Foreground = Brush(color), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(3) };
    private static SolidColorBrush Brush(string value) => new((WpfColor)WpfColorConverter.ConvertFromString(value));
}
