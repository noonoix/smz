using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;
using WpfButton = System.Windows.Controls.Button;
using WpfColor = System.Windows.Media.Color;
using WpfColorConverter = System.Windows.Media.ColorConverter;

namespace Ams.UI;

/// <summary>Visible Phase 7 Guard panel. All actions are observation/calibration protocol only.</summary>
internal static class LightGuardUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LightGuardUiInstalled", typeof(bool), typeof(LightGuardUiBootstrap), new PropertyMetadata(false));
    private static readonly DependencyProperty RetryHookInstalledProperty = DependencyProperty.RegisterAttached(
        "LightGuardUiRetryHookInstalled", typeof(bool), typeof(LightGuardUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true
            || window.DataContext is not MainViewModel vm) return;
        if (TryInstall(window, vm)) return;
        if (window.GetValue(RetryHookInstalledProperty) is true) return;
        window.SetValue(RetryHookInstalledProperty, true);

        EventHandler? layoutHandler = null;
        layoutHandler = (_, _) =>
        {
            if (!TryInstall(window, vm)) return;
            window.LayoutUpdated -= layoutHandler;
        };
        window.LayoutUpdated += layoutHandler;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            if (TryInstall(window, vm)) window.LayoutUpdated -= layoutHandler;
        }), System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static bool TryInstall(MainWindow window, MainViewModel vm)
    {
        var body = FindStatusBody(window);
        if (body is null) return false;
        if (ContainsText(body, "Light Guard — Phase 7"))
        {
            window.SetValue(InstalledProperty, true);
            return true;
        }

        vm.InitializeLightGuardAdapter();
        var content = new StackPanel();
        content.Children.Add(Text("Light Guard — Phase 7", 16, "#F5F7FA", FontWeights.SemiBold));
        content.Children.Add(Text(
            "Guard جدا از Phase 6 است: BH1750 روی GP20/GP21، GP4 شروع/توقف و hold سه‌ثانیه‌ای کالیبراسیون، GP3 Pass/Next، و GP6 passive piezo. هیچ RunEngine، HID، UART یا actuator در این مسیر نیست.",
            12, "#AAB3C2"));
        content.Children.Add(Text("کالیبراسیون فیزیکی: GP4 را ۳ ثانیه نگه دارید؛ برای هر جایگاه GP3 را بزنید. بعد از هر مرحلهٔ موفق، GP3 مرحلهٔ بعد را آماده می‌کند.", 12, "#DE9255"));
        content.Children.Add(Text("پیش‌فرض پروفایل جدید — فقط برای ایجاد/Reset؛ روی کالیبراسیون فعلی اثر ندارد", 12, "#AAB3C2"));
        var defaults = new WrapPanel { Margin = new Thickness(0, 4, 0, 4) };
        var tolerance = new TextBox { Width = 70, Text = vm.LightGuardDefaultTolerance.ToString("0.###"), Margin = new Thickness(4) };
        var stable = new TextBox { Width = 80, Text = vm.LightGuardDefaultStableDurationMs.ToString(), Margin = new Thickness(4) };
        var hysteresis = new TextBox { Width = 70, Text = vm.LightGuardDefaultHysteresisLux.ToString("0.###"), Margin = new Thickness(4) };
        defaults.Children.Add(Text("تلورانس", 11, "#D9DEE7")); defaults.Children.Add(tolerance);
        defaults.Children.Add(Text("پایداری ms", 11, "#D9DEE7")); defaults.Children.Add(stable);
        defaults.Children.Add(Text("hysteresis", 11, "#D9DEE7")); defaults.Children.Add(hysteresis);
        defaults.Children.Add(Action("ذخیره تنظیمات", "#4B5563", () =>
        {
            if (double.TryParse(tolerance.Text, out var t) && int.TryParse(stable.Text, out var s) && double.TryParse(hysteresis.Text, out var h))
            { vm.LightGuardDefaultTolerance = t; vm.LightGuardDefaultStableDurationMs = s; vm.LightGuardDefaultHysteresisLux = h; vm.SaveLightGuardDefaults(); }
            return Task.CompletedTask;
        }));
        content.Children.Add(defaults);

        var actions = new WrapPanel { Margin = new Thickness(0, 10, 0, 6) };
        actions.Children.Add(Action("باز کردن پنجره وضعیت", "#6B5E9E", () => { LightGuardStatusWindow.Show(window, vm); return Task.CompletedTask; }));
        actions.Children.Add(Action("دریافت از Pico", "#5E9FE8", async () => await vm.PullLightGuardCalibrationAsync()));
        actions.Children.Add(Action("مقایسه با Pico", "#B8893D", async () => await vm.CompareLightGuardCalibrationAsync()));
        actions.Children.Add(Action("شناسایی Guard / CALGET", "#5E9FE8", async () => await vm.RefreshLightGuardIdentityAsync()));
        actions.Children.Add(Action("ارسال به Pico", "#3D6B55", async () => await vm.SyncLightGuardCalibrationAsync()));
        actions.Children.Add(Action("Guard ON", "#3D6B55", async () => await vm.EnableLightGuardAsync()));
        actions.Children.Add(Action("Guard OFF", "#333740", async () => await vm.DisableLightGuardAsync()));
        content.Children.Add(actions);

        content.Children.Add(Bound(nameof(MainViewModel.LightGuardIdentityDisplay), 12, "#D9DEE7"));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardRevisionDisplay), 12, "#D9DEE7"));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardRevisionComparison), 12, "#DE9255"));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardCalibrationStatus), 12, "#72BC8F"));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardObservationStatus), 12, "#D9DEE7"));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardStateDisplay), 12, "#72BC8F", FontWeights.SemiBold));
        content.Children.Add(Bound(nameof(MainViewModel.LightGuardComparisonStatus), 12, "#DE9255", FontWeights.SemiBold));
        var comparison = new ItemsControl();
        comparison.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardComparisonDisplays)));
        content.Children.Add(comparison);

        var profiles = new ItemsControl();
        profiles.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardProfileDisplays)));
        profiles.Margin = new Thickness(3, 6, 3, 0);
        content.Children.Add(profiles);

        var card = new Border
        {
            Background = Brush("#22262D"), BorderBrush = Brush("#343B46"), BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8), Padding = new Thickness(14), Margin = new Thickness(4, 0, 4, 12),
            Child = content,
        };
        body.Children.Insert(Math.Max(0, body.Children.Count - 1), card);
        window.SetValue(InstalledProperty, true);
        return true;
    }

    private static WpfButton Action(string label, string background, Func<Task> action)
    {
        var button = new WpfButton
        {
            Content = label, Padding = new Thickness(12, 7, 12, 7), MinHeight = 36,
            Margin = new Thickness(6, 0, 0, 6), Background = Brush(background),
            Foreground = Brush("#F5F7FA"), FontWeight = FontWeights.SemiBold,
        };
        button.Click += async (_, _) => await action();
        return button;
    }

    private static TextBlock Bound(string path, double size, string color, FontWeight? weight = null)
    {
        var text = Text("", size, color, weight);
        text.SetBinding(TextBlock.TextProperty, new Binding(path));
        text.Margin = new Thickness(3, 2, 3, 2);
        return text;
    }

    private static TextBlock Text(string value, double size, string color, FontWeight? weight = null) => new()
    {
        Text = value, FontSize = size, FontWeight = weight ?? FontWeights.Normal, Foreground = Brush(color),
        TextWrapping = TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(3),
    };

    private static StackPanel? FindStatusBody(DependencyObject root)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is TextBlock title && title.Text.Contains("سنسور نور", StringComparison.Ordinal)
                && VisualTreeHelper.GetParent(title) is StackPanel body) return body;
            var found = FindStatusBody(child);
            if (found is not null) return found;
        }
        return null;
    }

    private static bool ContainsText(DependencyObject root, string text)
    {
        if (root is TextBlock block && block.Text == text) return true;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            if (ContainsText(VisualTreeHelper.GetChild(root, i), text)) return true;
        return false;
    }

    private static SolidColorBrush Brush(string color)
        => new((WpfColor)WpfColorConverter.ConvertFromString(color));
}
