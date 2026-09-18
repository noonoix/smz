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
using Ams.UI.Models;
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
        stack.Children.Add(BuildOverview(vm));
        stack.Children.Add(BuildWatch(vm));
        stack.Children.Add(BuildDiagnosis(vm));
        stack.Children.Add(BuildCalibrationSuggestion(vm));
        stack.Children.Add(BuildProfiles(vm));
        stack.Children.Add(BuildDefaults(vm));
        stack.Children.Add(BuildAuthorization(vm));
        stack.Children.Add(BuildGuard(vm));
        stack.Children.Add(BuildProfilesList(vm));

        _window = new Window
        {
            Title = "Status — Guard / Light",
            Owner = owner,
            Width = 1100,
            Height = 900,
            MinWidth = 820,
            MinHeight = 620,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = Brush("#22262D"),
            Content = new ScrollViewer { Content = stack, VerticalScrollBarVisibility = ScrollBarVisibility.Auto },
        };
        _window.Closed += (_, _) => _window = null;
        _window.Show();
    }

    private static UIElement BuildOverview(MainViewModel vm)
    {
        var grid = new Grid { Margin = new Thickness(0, 12, 0, 8) };
        for (var i = 0; i < 3; i++) grid.ColumnDefinitions.Add(new ColumnDefinition());
        AddCard(grid, vm, 0, "نور فعلی (Lux)", nameof(MainViewModel.CurrentLuxDisplay), "#F5F7FA");
        AddCard(grid, vm, 1, "آخرین نمونه", nameof(MainViewModel.LastLightSampleText), "#D9DEE7");
        AddCard(grid, vm, 2, "اتصال", nameof(MainViewModel.LightGuardIdentityDisplay), "#72BC8F");
        return grid;
    }

    private static UIElement BuildWatch(MainViewModel vm)
    {
        var box = new WpfGroupBox { Header = "وضعیت نور و پایش", Foreground = Brush("#F5F7FA"), Margin = new Thickness(0, 4, 0, 8) };
        var body = new StackPanel { Margin = new Thickness(10) };
        var grid = new Grid();
        for (var i = 0; i < 4; i++) grid.ColumnDefinitions.Add(new ColumnDefinition());
        for (var i = 0; i < 2; i++) grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        AddMetric(grid, vm, 0, 0, "وضعیت سنسور", nameof(MainViewModel.LightSensorStatus), "#72BC8F");
        AddMetric(grid, vm, 1, 0, "حالت سنسور", nameof(MainViewModel.LightSensorMode), "#D9DEE7");
        AddMetric(grid, vm, 2, 0, "تازگی داده", nameof(MainViewModel.LightFreshnessText), "#9CC7F2");
        AddMetric(grid, vm, 3, 0, "فاصله نمونه", nameof(MainViewModel.SelectedLightWatchIntervalMs), "#D9DEE7");
        AddMetric(grid, vm, 0, 1, "کمینه", nameof(MainViewModel.LightMinimumDisplay), "#D9DEE7");
        AddMetric(grid, vm, 1, 1, "میانگین", nameof(MainViewModel.LightAverageDisplay), "#D9DEE7");
        AddMetric(grid, vm, 2, 1, "بیشینه", nameof(MainViewModel.LightMaximumDisplay), "#D9DEE7");
        AddMetric(grid, vm, 3, 1, "دامنه تغییر", nameof(MainViewModel.LightSpreadDisplay), "#D9DEE7");
        body.Children.Add(grid);
        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(2, 8, 2, 0) };
        row.Children.Add(Text("فاصله نمونه‌برداری:", 12, FontWeights.Normal, "#D9DEE7"));
        var interval = new WpfComboBox { Width = 100, Margin = new Thickness(4), ItemsSource = vm.LightWatchIntervalsMs };
        interval.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightWatchIntervalMs)) { Source = vm, Mode = BindingMode.TwoWay });
        row.Children.Add(interval);
        row.Children.Add(Action("شروع پایش", "#5E9FE8", () => { vm.ToggleLightWatchCommand.Execute(null); return Task.CompletedTask; }));
        body.Children.Add(row); box.Content = body; return box;
    }

    private static UIElement BuildDiagnosis(MainViewModel vm)
    {
        var panel = new StackPanel { Margin = new Thickness(0, 6, 0, 8) };
        panel.Children.Add(Text("تشخیص وضعیت نور", 16, FontWeights.SemiBold));
        var grid = new Grid(); for (var i = 0; i < 3; i++) grid.ColumnDefinitions.Add(new ColumnDefinition());
        AddCard(grid, vm, 0, "وضعیت فعلی", nameof(MainViewModel.LightStateDisplay), "#F5F7FA");
        AddCard(grid, vm, 1, "اطمینان نمایشی", nameof(MainViewModel.LightStateConfidenceDisplay), "#D9DEE7");
        AddCard(grid, vm, 2, "آمادگی Launch / Auto Resume", nameof(MainViewModel.LightGateDiagnosticDisplay), "#DE9255");
        panel.Children.Add(grid);
        var warning = new Border { Background = Brush("#4A3020"), BorderBrush = Brush("#8A5A38"), BorderThickness = new Thickness(1), Padding = new Thickness(10), Margin = new Thickness(4) };
        warning.Child = Bound(vm, nameof(MainViewModel.LightStateWarning), "#F0B37E"); panel.Children.Add(warning); return panel;
    }

    private static UIElement BuildCalibrationSuggestion(MainViewModel vm)
    {
        var panel = Section("کالیبراسیون پیشنهادی", "از دادهٔ زنده پیشنهاد می‌سازد؛ تا «اعمال پیشنهاد» و سپس «ذخیره پروفایل‌ها» زده نشود هیچ مقدار تغییر نمی‌کند.");
        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(2, 8, 2, 4) };
        row.Children.Add(Text("پروفایل:", 12, FontWeights.Normal, "#D9DEE7"));
        var profile = new WpfComboBox { Width = 210, ItemsSource = vm.LightStateProfiles, DisplayMemberPath = "Name", Margin = new Thickness(4) };
        profile.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightCalibrationProfile)) { Source = vm, Mode = BindingMode.TwoWay }); row.Children.Add(profile);
        row.Children.Add(Text("مدت:", 12, FontWeights.Normal, "#D9DEE7"));
        var duration = new WpfComboBox { Width = 80, ItemsSource = vm.LightCalibrationDurationsSeconds, Margin = new Thickness(4) };
        duration.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightCalibrationDurationSeconds)) { Source = vm, Mode = BindingMode.TwoWay }); row.Children.Add(duration);
        row.Children.Add(Action("شروع نمونه‌برداری", "#5E9FE8", () => { vm.StartLightProfileCalibration(); return Task.CompletedTask; }));
        row.Children.Add(Action("لغو", "#333740", () => { vm.CancelLightProfileCalibration(); return Task.CompletedTask; }));
        row.Children.Add(Action("اعمال پیشنهاد روی فرم", "#3D6B55", () => { vm.ApplyPendingLightCalibrationSuggestion(); return Task.CompletedTask; }));
        panel.Children.Add(row); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightCalibrationStatus))); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightCalibrationSuggestionDisplay), "#72BC8F")); return panel;
    }

    private static UIElement BuildProfiles(MainViewModel vm)
    {
        var panel = Section("پروفایل‌های قابل تنظیم", "مرکز و تلورانس فعلی قابل ویرایش است؛ ذخیرهٔ این فرم روی کالیبراسیون فیزیکی برد overwrite نمی‌کند.");
        var grid = new Grid { Margin = new Thickness(0, 8, 0, 4) };
        for (var i = 0; i < 7; i++) grid.ColumnDefinitions.Add(new ColumnDefinition { Width = i == 1 ? new GridLength(2, GridUnitType.Star) : new GridLength(1, GridUnitType.Star) });
        AddHeader(grid, "فعال", 0); AddHeader(grid, "نام وضعیت", 1); AddHeader(grid, "مرکز", 2); AddHeader(grid, "تلورانس ±", 3); AddHeader(grid, "بازه مؤثر", 4); AddHeader(grid, "پایداری ms", 5); AddHeader(grid, "Hysteresis", 6);
        foreach (var p in vm.LightStateProfiles)
        {
            var row = new Grid { Margin = new Thickness(0, 2, 0, 2) };
            for (var i = 0; i < 7; i++) row.ColumnDefinitions.Add(new ColumnDefinition { Width = i == 1 ? new GridLength(2, GridUnitType.Star) : new GridLength(1, GridUnitType.Star) });
            var check = new CheckBox { IsChecked = p.Enabled, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center }; check.Checked += (_, _) => p.Enabled = true; check.Unchecked += (_, _) => p.Enabled = false; Add(row, check, 0);
            Add(row, Edit(p, nameof(p.Name)), 1); Add(row, Edit(p, nameof(p.LuxCenter)), 2); Add(row, Edit(p, nameof(p.LuxTolerance)), 3); Add(row, Text($"{p.LuxMin:0.#} تا {p.LuxMax:0.#}", 12, FontWeights.Normal, "#D9DEE7"), 4); Add(row, Edit(p, nameof(p.StableDurationMs)), 5); Add(row, Edit(p, nameof(p.HysteresisLux)), 6); grid.Children.Add(row);
        }
        panel.Children.Add(grid);
        var actions = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right }; actions.Children.Add(Action("ذخیره پروفایل‌ها", "#5E9FE8", () => { vm.SaveLightStateProfiles(); return Task.CompletedTask; })); actions.Children.Add(Action("بازگردانی مقادیر اولیه", "#333740", () => { vm.ResetLightStateProfiles(); return Task.CompletedTask; })); panel.Children.Add(actions); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightProfileSaveStatus))); return panel;
    }

    private static UIElement BuildDefaults(MainViewModel vm)
    {
        var panel = Section("تنظیمات پیش‌فرض Guard", "این مقادیر برای پروفایل‌های جدید استفاده می‌شوند و روی کالیبراسیون فعلی برد اثر ندارند.");
        var row = new StackPanel { Orientation = Orientation.Horizontal };
        row.Children.Add(Field("تلورانس ±", nameof(MainViewModel.LightGuardDefaultTolerance), vm)); row.Children.Add(Field("پایداری ms", nameof(MainViewModel.LightGuardDefaultStableDurationMs), vm)); row.Children.Add(Field("Hysteresis", nameof(MainViewModel.LightGuardDefaultHysteresisLux), vm)); row.Children.Add(Action("ذخیره تنظیمات", "#5E9FE8", () => { vm.SaveLightGuardDefaults(); return Task.CompletedTask; })); panel.Children.Add(row); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightProfileSaveStatus))); return panel;
    }

    private static UIElement BuildAuthorization(MainViewModel vm)
    {
        var panel = Section("مجوز تشخیصی نور", "این کارت فقط برای آزمایش قرارداد Permit/Arm است؛ هیچ Macro، Launch، Recovery، HID یا Arm واقعی اجرا نمی‌شود.");
        var row = new StackPanel { Orientation = Orientation.Horizontal };
        var target = new WpfComboBox { Width = 190, ItemsSource = vm.LightAuthorizationIntentOptions, Margin = new Thickness(4) }; target.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightAuthorizationIntent)) { Source = vm, Mode = BindingMode.TwoWay }); row.Children.Add(target);
        row.Children.Add(Action("Arm تشخیصی", "#5E9FE8", () => { vm.ArmLightAuthorizationDiagnostic(); return Task.CompletedTask; })); row.Children.Add(Action("Issue Permit", "#3D6B55", () => { vm.IssueLightAuthorizationDiagnosticPermit(); return Task.CompletedTask; })); row.Children.Add(Action("Consume بدون اجرا", "#3D6B55", () => { vm.ConsumeLightAuthorizationDiagnosticPermit(); return Task.CompletedTask; })); row.Children.Add(Action("Revoke", "#333740", () => { vm.RevokeLightAuthorizationDiagnostic(); return Task.CompletedTask; })); panel.Children.Add(row); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightAuthorizationDiagnosticDisplay))); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay), "#DE9255")); return panel;
    }

    private static UIElement BuildGuard(MainViewModel vm)
    {
        var panel = Section("وضعیت Guard — Phase 7", "Guard، کالیبراسیون فیزیکی و همگام‌سازی Pico در همین پنجره در دسترس هستند."); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardIdentityDisplay))); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardRevisionDisplay))); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardRevisionComparison), "#DE9255")); panel.Children.Add(Bound(vm, nameof(MainViewModel.LightGuardCalibrationStatus), "#72BC8F")); var row = new StackPanel { Orientation = Orientation.Horizontal }; row.Children.Add(Action("دریافت از Pico", "#5E9FE8", () => vm.PullLightGuardCalibrationAsync())); row.Children.Add(Action("ارسال به Pico", "#3D6B55", () => vm.SyncLightGuardCalibrationAsync())); row.Children.Add(Action("CALGET", "#4B5563", () => vm.RefreshLightGuardIdentityAsync())); row.Children.Add(Action("Guard OFF", "#333740", () => vm.DisableLightGuardAsync())); row.Children.Add(Action("Guard ON", "#3D6B55", () => vm.EnableLightGuardAsync())); row.Children.Add(Action("اجرای dry-run", "#8A6D3B", () => vm.RunSessionCycleDryRunAsync())); row.Children.Add(Action("لغو dry-run", "#7A3E3E", () => { vm.CancelSessionCycleDryRun(); return Task.CompletedTask; })); panel.Children.Add(row); return panel;
    }

    private static UIElement BuildProfilesList(MainViewModel vm)
    {
        var panel = Section("پروفایل‌های Guard روی برد", "وضعیت شش پروفایل و revision فعلی Pico."); var list = new ItemsControl(); list.SetBinding(ItemsControl.ItemsSourceProperty, new Binding(nameof(MainViewModel.LightGuardProfileDisplays)) { Source = vm }); panel.Children.Add(list); return panel;
    }

    private static StackPanel Section(string title, string subtitle)
    { var p = new StackPanel { Margin = new Thickness(0, 8, 0, 8) }; p.Children.Add(Text(title, 16, FontWeights.SemiBold)); p.Children.Add(Text(subtitle, 12, FontWeights.Normal, "#AAB3C2")); return p; }
    private static FrameworkElement Field(string label, string binding, MainViewModel vm)
    { var p = new StackPanel { Margin = new Thickness(4) }; p.Children.Add(Text(label, 11, FontWeights.Normal, "#AAB3C2")); var b = new TextBox { Width = 90, Margin = new Thickness(2), Padding = new Thickness(5), Background = Brush("#181B20"), Foreground = Brush("#F5F7FA") }; b.SetBinding(TextBox.TextProperty, new Binding(binding) { Source = vm, Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.LostFocus }); p.Children.Add(b); return p; }
    private static TextBox Edit(object source, string path) { var b = new TextBox { Margin = new Thickness(2), Padding = new Thickness(5), Background = Brush("#181B20"), Foreground = Brush("#F5F7FA") }; b.SetBinding(TextBox.TextProperty, new Binding(path) { Source = source, Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.LostFocus, ValidatesOnExceptions = true }); return b; }
    private static Button Action(string label, string bg, Func<Task> action) { var b = new Button { Content = label, Padding = new Thickness(11, 6, 11, 6), Margin = new Thickness(4), Background = Brush(bg), Foreground = Brush("#F5F7FA") }; b.Click += async (_, _) => await action(); return b; }
    private static void AddHeader(Grid g, string text, int col) => Add(g, Text(text, 11, FontWeights.Normal, "#AAB3C2"), col);
    private static void AddMetric(Grid g, MainViewModel vm, int col, int row, string label, string path, string color) { var p = new StackPanel { Margin = new Thickness(4) }; p.Children.Add(Text(label, 11, FontWeights.Normal, "#AAB3C2")); p.Children.Add(Bound(vm, path, color)); Grid.SetColumn(p, col); Grid.SetRow(p, row); g.Children.Add(p); }
    private static void AddCard(Grid g, MainViewModel vm, int col, string label, string path, string color) { var b = new Border { Background = Brush("#252A32"), BorderBrush = Brush("#353C47"), BorderThickness = new Thickness(1), Padding = new Thickness(10), Margin = new Thickness(4), Child = new StackPanel() }; ((StackPanel)b.Child).Children.Add(Text(label, 11, FontWeights.Normal, "#AEB8C8")); ((StackPanel)b.Child).Children.Add(Bound(vm, path, color)); Grid.SetColumn(b, col); g.Children.Add(b); }
    private static void Add(Grid g, UIElement e, int col) { Grid.SetColumn(e, col); g.Children.Add(e); }
    private static TextBlock Bound(MainViewModel vm, string path, string color = "#D9DEE7") { var t = Text("", 13, FontWeights.Normal, color); t.SetBinding(TextBlock.TextProperty, new Binding(path) { Source = vm }); return t; }
    private static TextBlock Text(string value, double size, FontWeight weight, string color = "#F5F7FA") => new() { Text = value, FontSize = size, FontWeight = weight, Foreground = Brush(color), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(3) };
    private static SolidColorBrush Brush(string color) => new((WpfColor)WpfColorConverter.ConvertFromString(color));
}
