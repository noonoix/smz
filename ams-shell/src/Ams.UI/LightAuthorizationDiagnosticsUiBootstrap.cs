using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;
using WpfButton = System.Windows.Controls.Button;
using WpfColor = System.Windows.Media.Color;
using WpfColorConverter = System.Windows.Media.ColorConverter;
using WpfComboBox = System.Windows.Controls.ComboBox;

namespace Ams.UI;

/// <summary>
/// Adds the explicit, non-executing authorization diagnostics card to the existing Status surface.
/// Every action is a manual ledger operation; this class has no runtime, bridge or actuator access.
/// </summary>
internal static class LightAuthorizationDiagnosticsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LightAuthorizationDiagnosticsUiInstalled", typeof(bool),
        typeof(LightAuthorizationDiagnosticsUiBootstrap), new PropertyMetadata(false));

    private static readonly DependencyProperty RetryHookInstalledProperty = DependencyProperty.RegisterAttached(
        "LightAuthorizationDiagnosticsUiRetryHookInstalled", typeof(bool),
        typeof(LightAuthorizationDiagnosticsUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window
            || window.GetValue(InstalledProperty) is true
            || window.DataContext is not MainViewModel vm)
            return;

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
        if (ContainsText(body, "مجوز تشخیصی نور"))
        {
            window.SetValue(InstalledProperty, true);
            return true;
        }

        var section = BuildSection(vm);
        var insertAt = Math.Max(0, body.Children.Count - 1);
        body.Children.Insert(insertAt, section);
        window.SetValue(InstalledProperty, true);
        return true;
    }

    private static Border BuildSection(MainViewModel vm)
    {
        var section = new StackPanel { Margin = new Thickness(0, 12, 0, 0) };
        section.Children.Add(Text("مجوز تشخیصی نور", 19, "#F5F7FA", FontWeights.SemiBold));
        section.Children.Add(Text(
            "این کارت فقط برای آزمایش قرارداد Arm/Permit است؛ هیچ Macro، Launch، Recovery، HID یا فرمان برد اجرا نمی‌شود.",
            12, "#AAB3C2"));

        var warning = new Border
        {
            Background = Brush("#3A2B20"),
            BorderBrush = Brush("#8B5A32"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(12),
            Margin = new Thickness(4, 10, 4, 10),
            Child = Text("فقط تشخیصی — بدون اجرا", 14, "#DE9255", FontWeights.SemiBold),
        };
        section.Children.Add(warning);

        var intentRow = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            FlowDirection = FlowDirection.RightToLeft,
            Margin = new Thickness(4, 0, 4, 8),
        };
        intentRow.Children.Add(Text("هدف تشخیصی:", 12, "#D9DEE7"));
        var intent = new WpfComboBox
        {
            Width = 220,
            MinHeight = 34,
            Margin = new Thickness(8, 0, 0, 0),
            ItemsSource = vm.LightAuthorizationIntentOptions,
        };
        intent.SetBinding(WpfComboBox.SelectedItemProperty, new Binding(nameof(MainViewModel.SelectedLightAuthorizationIntent))
        {
            Source = vm,
            Mode = BindingMode.TwoWay,
            UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged,
        });
        intentRow.Children.Add(intent);
        section.Children.Add(intentRow);

        var actions = new WrapPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            Margin = new Thickness(4, 0, 4, 8),
        };
        var arm = ActionButton("Arm تشخیصی", "#5E9FE8", "#10151C");
        arm.Click += (_, _) => vm.ArmLightAuthorizationDiagnostic();
        actions.Children.Add(arm);

        var issue = ActionButton("Issue Permit تشخیصی", "#3D6B55", "#F5F7FA");
        issue.SetBinding(UIElement.IsEnabledProperty, new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticIsActive))
        {
            Source = vm,
        });
        issue.Click += (_, _) => vm.IssueLightAuthorizationDiagnosticPermit();
        actions.Children.Add(issue);

        var consume = ActionButton("Consume بدون اجرا", "#3D6B55", "#F5F7FA");
        consume.SetBinding(UIElement.IsEnabledProperty, new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticIsActive))
        {
            Source = vm,
        });
        consume.Click += (_, _) => vm.ConsumeLightAuthorizationDiagnosticPermit();
        actions.Children.Add(consume);

        var revoke = ActionButton("Revoke", "#333740", "#F5F7FA");
        revoke.Click += (_, _) => vm.RevokeLightAuthorizationDiagnostic();
        actions.Children.Add(revoke);
        section.Children.Add(actions);

        var state = Text("", 15, "#F5F7FA", FontWeights.SemiBold);
        state.SetBinding(TextBlock.TextProperty, new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticDisplay))
        {
            Source = vm,
        });
        state.SetBinding(FrameworkElement.ToolTipProperty, new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay))
        {
            Source = vm,
        });
        state.Margin = new Thickness(4, 4, 4, 2);
        section.Children.Add(state);

        var reason = Text("", 12, "#AAB3C2");
        reason.SetBinding(TextBlock.TextProperty, new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay))
        {
            Source = vm,
            StringFormat = "Reason: {0}",
        });
        reason.Margin = new Thickness(4, 0, 4, 4);
        section.Children.Add(reason);

        var card = new Border
        {
            Background = Brush("#22262D"),
            BorderBrush = Brush("#343B46"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Padding = new Thickness(14),
            Margin = new Thickness(4, 0, 4, 12),
            Child = section,
        };
        return card;
    }

    private static Button ActionButton(string label, string background, string foreground) => new()
    {
        Content = label,
        Padding = new Thickness(12, 7, 12, 7),
        MinHeight = 36,
        Margin = new Thickness(6, 0, 0, 6),
        Background = Brush(background),
        Foreground = Brush(foreground),
        FontWeight = FontWeights.SemiBold,
    };

    private static TextBlock Text(string value, double size, string color, FontWeight? weight = null) => new()
    {
        Text = value,
        FontSize = size,
        FontWeight = weight ?? FontWeights.Normal,
        Foreground = Brush(color),
        TextWrapping = TextWrapping.Wrap,
        VerticalAlignment = VerticalAlignment.Center,
        Margin = new Thickness(3),
    };

    private static StackPanel? FindStatusBody(DependencyObject root)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is TextBlock { Text: "وضعیت زنده‌ی سنسور نور" } title
                && VisualTreeHelper.GetParent(title) is StackPanel body)
                return body;
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
