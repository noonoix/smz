using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Threading;
using Ams.UI.Services;
using Ams.UI.ViewModels;
using WpfColor = System.Windows.Media.Color;
using WpfColorConverter = System.Windows.Media.ColorConverter;

namespace Ams.UI;

/// <summary>Adds manual, non-executing authorization diagnostics after the phase-five gate cards.</summary>
internal static class LightAuthorizationDiagnosticsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LightAuthorizationDiagnosticsInstalled", typeof(bool), typeof(LightAuthorizationDiagnosticsUiBootstrap),
        new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true
            || window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);

        vm.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(MainViewModel.Connection)
                && vm.Connection != ConnectionState.Connected
                && vm.LightAuthorizationDiagnosticIsActive)
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.Disconnected);
            else if (args.PropertyName == nameof(MainViewModel.FileText)
                     && vm.LightAuthorizationDiagnosticIsActive)
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.PipelineChanged);
        };

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
        }), DispatcherPriority.ContextIdle);
    }

    private static bool TryInstall(MainWindow window, MainViewModel vm)
    {
        if (ContainsText(window, "مجوز تشخیصی — بدون اجرا")) return true;
        var section = FindStatusSection(window);
        if (section is null) return false;

        var card = new Border
        {
            Background = Brush("#22262D"), BorderBrush = Brush("#4A5360"),
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8),
            Padding = new Thickness(14), Margin = new Thickness(4, 0, 4, 10),
        };
        var body = new StackPanel();
        body.Children.Add(Text("مجوز تشخیصی — بدون اجرا", 15, "#F5F7FA", FontWeights.SemiBold));
        body.Children.Add(Text("Arm، صدور و مصرف فقط Ledger داخلی را تغییر می‌دهند؛ هیچ Macro، Launch یا فرمان برد اجرا نمی‌شود.",
            12, "#DE9255"));

        var actions = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 10, 0, 8) };
        var intents = new ComboBox { Width = 180, Padding = new Thickness(6, 4, 6, 4), Margin = new Thickness(3) };
        intents.SetBinding(ItemsControl.ItemsSourceProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationIntentOptions)) { Source = vm });
        intents.SetBinding(ComboBox.SelectedItemProperty,
            new Binding(nameof(MainViewModel.SelectedLightAuthorizationIntent))
            { Source = vm, Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
        actions.Children.Add(intents);

        var arm = Button("Arm تشخیصی");
        arm.Click += (_, _) => vm.ArmLightAuthorizationDiagnostic();
        var issue = Button("صدور Permit");
        issue.Click += (_, _) => vm.IssueLightAuthorizationDiagnosticPermit();
        var consume = Button("مصرف بدون اجرا");
        consume.Click += (_, _) => vm.ConsumeLightAuthorizationDiagnosticPermit();
        var revoke = Button("ابطال");
        revoke.Click += (_, _) => vm.RevokeLightAuthorizationDiagnostic();
        actions.Children.Add(arm); actions.Children.Add(issue); actions.Children.Add(consume); actions.Children.Add(revoke);
        body.Children.Add(actions);

        var state = Text("", 13, "#D9DEE7", FontWeights.SemiBold);
        state.SetBinding(TextBlock.TextProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticDisplay)) { Source = vm });
        state.SetBinding(FrameworkElement.ToolTipProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay)) { Source = vm });
        body.Children.Add(state);
        card.Child = body;

        var insertAt = Math.Min(2, section.Children.Count);
        section.Children.Insert(insertAt, card);
        return true;
    }

    private static Button Button(string text) => new()
    {
        Content = text, Padding = new Thickness(12, 6, 12, 6), Margin = new Thickness(3),
        Background = Brush("#333A45"), Foreground = Brush("#F5F7FA"), MinHeight = 34,
    };

    private static TextBlock Text(string text, double size, string color, FontWeight? weight = null) => new()
    {
        Text = text, FontSize = size, Foreground = Brush(color), FontWeight = weight ?? FontWeights.Normal,
        TextWrapping = TextWrapping.Wrap, Margin = new Thickness(3),
    };

    private static StackPanel? FindStatusSection(DependencyObject root)
    {
        if (root is TextBlock { Text: "تشخیص وضعیت نور" } title
            && VisualTreeHelper.GetParent(title) is StackPanel section) return section;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var found = FindStatusSection(VisualTreeHelper.GetChild(root, i));
            if (found is not null) return found;
        }
        return null;
    }

    private static bool ContainsText(DependencyObject root, string value)
    {
        if (root is TextBlock block && block.Text == value) return true;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            if (ContainsText(VisualTreeHelper.GetChild(root, i), value)) return true;
        return false;
    }

    private static SolidColorBrush Brush(string color)
        => new((WpfColor)WpfColorConverter.ConvertFromString(color));
}
