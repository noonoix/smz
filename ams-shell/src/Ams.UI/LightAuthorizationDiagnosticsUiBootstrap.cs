using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.Services;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Manual authorization diagnostics UI. Every action remains non-executing.</summary>
internal static class LightAuthorizationDiagnosticsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "AuthorizationDiagnosticsInstalled", typeof(bool), typeof(LightAuthorizationDiagnosticsUiBootstrap),
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
            if (!vm.LightAuthorizationDiagnosticIsActive) return;
            if (args.PropertyName == nameof(MainViewModel.Connection)
                && vm.Connection != ConnectionState.Connected)
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.Disconnected);
            else if (args.PropertyName == nameof(MainViewModel.FileText))
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.PipelineChanged);
        };

        EventHandler? retry = null;
        retry = (_, _) =>
        {
            if (!TryInstall(window, vm)) return;
            window.LayoutUpdated -= retry;
        };
        window.LayoutUpdated += retry;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            if (TryInstall(window, vm)) window.LayoutUpdated -= retry;
        }), System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static bool TryInstall(MainWindow window, MainViewModel vm)
    {
        var section = FindStatusSection(window);
        if (section is null) return false;
        if (section.Children.OfType<Border>().Any(x => Equals(x.Tag, "authorization-diagnostics"))) return true;

        var body = new StackPanel();
        body.Children.Add(MakeText("مجوز تشخیصی — بدون اجرا", 15, "#F5F7FA"));
        body.Children.Add(MakeText(
            "Arm، صدور و مصرف فقط Ledger داخلی را تغییر می‌دهند؛ هیچ فرمانی اجرا نمی‌شود.",
            12, "#DE9255"));

        var row = new WrapPanel { Margin = new Thickness(0, 8, 0, 8) };
        var intents = new ComboBox { Width = 180, Padding = new Thickness(6, 4, 6, 4), Margin = new Thickness(3) };
        intents.SetBinding(ItemsControl.ItemsSourceProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationIntentOptions)) { Source = vm });
        intents.SetBinding(ComboBox.SelectedItemProperty,
            new Binding(nameof(MainViewModel.SelectedLightAuthorizationIntent))
            { Source = vm, Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
        row.Children.Add(intents);
        row.Children.Add(MakeButton("Arm تشخیصی", vm.ArmLightAuthorizationDiagnostic));
        row.Children.Add(MakeButton("صدور Permit", vm.IssueLightAuthorizationDiagnosticPermit));
        row.Children.Add(MakeButton("مصرف بدون اجرا", vm.ConsumeLightAuthorizationDiagnosticPermit));
        row.Children.Add(MakeButton("ابطال", () => vm.RevokeLightAuthorizationDiagnostic()));
        body.Children.Add(row);

        var state = MakeText("", 13, "#D9DEE7");
        state.SetBinding(TextBlock.TextProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticDisplay)) { Source = vm });
        state.SetBinding(FrameworkElement.ToolTipProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay)) { Source = vm });
        body.Children.Add(state);

        var card = new Border
        {
            Tag = "authorization-diagnostics", Child = body,
            Background = MakeBrush("#22262D"), BorderBrush = MakeBrush("#4A5360"),
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8),
            Padding = new Thickness(14), Margin = new Thickness(4, 0, 4, 10),
        };
        section.Children.Insert(Math.Min(2, section.Children.Count), card);
        return true;
    }

    private static Button MakeButton(string label, Action action)
    {
        var button = new Button
        {
            Content = label, Padding = new Thickness(12, 6, 12, 6), Margin = new Thickness(3),
            Background = MakeBrush("#333A45"), Foreground = MakeBrush("#F5F7FA"), MinHeight = 34,
        };
        button.Click += (_, _) => action();
        return button;
    }

    private static TextBlock MakeText(string value, double size, string color) => new()
    {
        Text = value, FontSize = size, Foreground = MakeBrush(color),
        TextWrapping = TextWrapping.Wrap, Margin = new Thickness(3),
    };

    private static StackPanel? FindStatusSection(DependencyObject root)
    {
        if (root is TextBlock { Text: "تشخیص وضعیت نور" } title
            && VisualTreeHelper.GetParent(title) is StackPanel panel) return panel;
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(root); index++)
        {
            var found = FindStatusSection(VisualTreeHelper.GetChild(root, index));
            if (found is not null) return found;
        }
        return null;
    }

    private static SolidColorBrush MakeBrush(string value)
        => new((Color)ColorConverter.ConvertFromString(value));
}
