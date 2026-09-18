using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using WpfColor = System.Windows.Media.Color;
using WpfColorConverter = System.Windows.Media.ColorConverter;
using WpfComboBox = System.Windows.Controls.ComboBox;
using WpfGroupBox = System.Windows.Controls.GroupBox;
using Ams.UI.ViewModels;

namespace Ams.UI;

internal static class LightGuardStatusWindow
{
    private static Window? _window;

    public static void Show(Window owner, MainViewModel vm)
    {
        if (_window is { IsVisible: true }) { _window.Activate(); return; }
        var stack = new StackPanel { Margin = new Thickness(18) };
        stack.Children.Add(Text("وضعیت زندهٔ سنسور نور", 19, FontWeights.SemiBold));
        stack.Children.Add(Text("پایش فقط خواندنی است؛ تغییر نور هیچ ماکرو یا فرمان Armed را اجرا نمی‌کند.", 13, FontWeights.Normal, "#9CC7F2"));

        var overview = new Grid { Margin = new Thickness(0, 12, 0, 8) };
        for (var i = 0; i < 3; i++) overview.ColumnDefinitions.Add(new ColumnDefinition());
        AddCard(overview, vm, 0, "نور فعلی (Lux)", nameof(MainViewModel.CurrentLuxDisplay), "#F5F7FA");
        AddCard(overview, vm, 1, "آخرین نمونه", nameof(MainViewModel.LastLightSampleText), "#D9DEE7");
        AddCard(overview, vm, 2, "اتصال", nameof(MainViewModel.LightGuardIdentityDisplay), "#72BC8F");
        stack.Children.Add(overview);

        var watch = new WpfGroupBox { Header = "وضعیت نور و پایش", Foreground = Brush("#F5F7FA"), Margin = new Thickness(0, 4, 0, 8) };
        var watchPanel = new StackPanel { Margin = new Thickness(10) };
        var watchGrid = new Grid();
        for (var i = 0; i < 4; i++) watchGrid.ColumnDefinitions.Add(new ColumnDefinition());
        for (var i = 0; i < 2; i++) watchGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        AddMetric(watchGrid, vm, 0, 0, "وضعیت سنسور", nameof(MainViewModel.LightSensorStatus), "#72BC8F");
        AddMetric(watchGrid, vm, 1, 0, "حالت سنسور", nameof(MainViewModel.LightSensorMode), "#D9DEE7");
        AddMetric(watchGrid, vm, 2, 0, "تازگی داده", nameof(MainViewModel.LightFreshnessText), "#9CC7F2");
        AddMetric(watchGrid, vm, 3, 0, "فاصله نمونه", nameof(MainViewModel.SelectedLightWatchIntervalMs), "#D9DEE7");
        AddMetric(watchGrid, vm, 0, 1, "کمینه", nameof(MainViewModel.LightMinimumDisplay), "#D9DEE7");
        AddMetric(watchGrid, vm, 1, 1, "میانگین", nameof(MainViewModel.LightAverageDisplay), "#D9DEE7");
        AddMetric(watchGrid, vm, 2, 1, "بیشینه", nameof(MainViewModel.LightMaximumDisplay), "#D9DEE7");
        AddMetric(watchGrid, vm, 3, 1, "دامنه تغییر", nameof(MainViewModel.LightSpreadDisplay), "#D9DEE7");
        watchPanel.Children.Add(watchGrid);
        var controls = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(2, 8, 2, 0) };
        controls.Children.Add(new TextBlock { Text = "فاصله نمونه‌برداری:", Foreground = Brush("#D9DEE7"), VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(3) });
        var interval = new WpfComboBox { Width = 100, Margin = new Thickness(4), ItemsSource = vm.LightWatchIntervalsMs };
        interval.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightWatchIntervalMs)) { Source = vm, Mode = BindingMode.TwoWay });
        controls.Children.Add(interval);
        var watchButton = new Button { Padding = new Thickness(12, 6, 12, 6), Margin = new Thickness(4), Background = Brush("#5E9FE8"), Foreground = Brush("#F5F7FA") };
        watchButton.SetBinding(Button.ContentProperty, new Binding(nameof(MainViewModel.LightWatchButtonText)) { Source = vm });
        watchButton.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.ToggleLightWatchCommand)) { Source = vm });
        controls.Children.Add(watchButton);
        watchPanel.Children.Add(controls);
        watch.Content = watchPanel;
        stack.Children.Add(watch);

        stack.Children.Add(Text("تشخیص وضعیت نور", 16, FontWeights.SemiBold));
        var diagnosis = new Grid { Margin = new Thickness(0, 4, 0, 8) };
        for (var i = 0; i < 3; i++) diagnosis.ColumnDefinitions.Add(new ColumnDefinition());
        AddCard(diagnosis, vm, 0, "وضعیت فعلی", nameof(MainViewModel.LightGuardStateDisplay), "#F5F7FA");
        AddCard(diagnosis, vm, 1, "اطمینان نمایشی", nameof(MainViewModel.LightGuardObservationStatus), "#D9DEE7");
        AddCard(diagnosis, vm, 2, "آمادگی Launch / Auto Resume", nameof(MainViewModel.SessionCycleDryRunStatus), "#DE9255");
        stack.Children.Add(diagnosis);
        var warning = new Border { Background = Brush("#4A3020"), BorderBrush = Brush("#8A5A38"), BorderThickness = new Thickness(1), Padding = new Thickness(10), Margin = new Thickness(0, 2, 0, 10) };
        warning.Child = Bound(vm, nameof(MainViewModel.LightGuardRevisionComparison), "#F0B37E");
        stack.Children.Add(warning);

        stack.Children.Add(Text("وضعیت Guard — Phase 7", 18, FontWeights.SemiBold));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardRevisionDisplay)));
        stack.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardCalibrationStatus), "#72BC8F"));
        var actions = new WrapPanel { Margin = new Thickness(0, 12, 0, 0) };
        actions.Children.Add(Action("دریافت از Pico", "#5E9FE8", () => vm.PullLightGuardCalibrationAsync()));
        actions.Children.Add(Action("ارسال به Pico", "#3D6B55", () => vm.SyncLightGuardCalibrationAsync()));
        actions.Children.Add(Action("CALGET", "#4B5563", () => vm.RefreshLightGuardIdentityAsync()));
        actions.Children.Add(Action("Guard OFF", "#333740", () => vm.DisableLightGuardAsync()));
        actions.Children.Add(Action("Guard ON", "#3D6B55", () => vm.EnableLightGuardAsync()));
        actions.Children.Add(Action("اجرای dry-run چرخهٔ ۵گانه", "#8A6D3B", () => vm.RunSessionCycleDryRunAsync()));
        actions.Children.Add(Action("لغو dry-run", "#7A3E3E", () => { vm.CancelSessionCycleDryRun(); return Task.CompletedTask; }));
        stack.Children.Add(actions);
        var profiles = new ItemsControl();
        profiles.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardProfileDisplays)) { Source = vm });
        stack.Children.Add(profiles);

        _window = new Window
        {
            Title = "Status — Guard / Light",
            Owner = owner,
            Width = 980,
            Height = 760,
            MinWidth = 760,
            MinHeight = 560,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = Brush("#22262D"),
            Content = new ScrollViewer { Content = stack, VerticalScrollBarVisibility = ScrollBarVisibility.Auto },
        };
        _window.Closed += (_, _) => _window = null;
        _window.Show();
    }

    private static void AddCard(Grid grid, MainViewModel vm, int column, string label, string binding, string color)
    {
        var border = new Border { Background = Brush("#252A32"), BorderBrush = Brush("#353C47"), BorderThickness = new Thickness(1), Padding = new Thickness(10), Margin = new Thickness(4) };
        var panel = new StackPanel();
        panel.Children.Add(Text(label, 11, FontWeights.Normal, "#AEB8C8"));
        panel.Children.Add(Bound(vm, binding, color));
        border.Child = panel;
        Grid.SetColumn(border, column);
        grid.Children.Add(border);
    }

    private static void AddMetric(Grid grid, MainViewModel vm, int column, int row, string label, string binding, string color)
    {
        var panel = new StackPanel { Margin = new Thickness(4, 3, 12, 3) };
        panel.Children.Add(Text(label, 11, FontWeights.Normal, "#AEB8C8"));
        panel.Children.Add(Bound(vm, binding, color));
        Grid.SetColumn(panel, column);
        Grid.SetRow(panel, row);
        grid.Children.Add(panel);
    }

    private static Button Action(string label, string background, Func<Task> action)
    { var b = new Button { Content = label, Padding = new Thickness(12, 7, 12, 7), Margin = new Thickness(4), Background = Brush(background), Foreground = Brush("#F5F7FA") }; b.Click += async (_, _) => await action(); return b; }
    private static TextBlock Bound(MainViewModel vm, string path, string color = "#D9DEE7") { var t = Text("", 13, FontWeights.Normal, color); t.SetBinding(TextBlock.TextProperty, new Binding(path) { Source = vm }); return t; }
    private static TextBlock Text(string value, double size, FontWeight weight, string color = "#F5F7FA") => new() { Text = value, FontSize = size, FontWeight = weight, Foreground = Brush(color), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(3) };
    private static SolidColorBrush Brush(string value) => new((WpfColor)WpfColorConverter.ConvertFromString(value));
}
