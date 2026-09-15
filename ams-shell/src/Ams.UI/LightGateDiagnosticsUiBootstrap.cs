using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.Services;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Binds read-only gate diagnostics and installs the manual non-executing authorization card.
/// Lifecycle tracking is installed immediately; visual work retries until Status exists.
/// </summary>
internal static class LightGateDiagnosticsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "LightGateDiagnosticsInstalled", typeof(bool), typeof(LightGateDiagnosticsUiBootstrap),
        new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window
            || window.GetValue(InstalledProperty) is true
            || window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);

        vm.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(MainViewModel.IsLightWatchRunning))
            {
                if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
                else vm.StopLightGateDiagnosticSession();
                return;
            }
            if (!vm.LightAuthorizationDiagnosticIsActive) return;
            if (args.PropertyName == nameof(MainViewModel.Connection)
                && vm.Connection != ConnectionState.Connected)
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.Disconnected);
            else if (args.PropertyName == nameof(MainViewModel.FileText))
                vm.RevokeLightAuthorizationDiagnostic(LightAuthorizationReasonCode.PipelineChanged);
        };
        if (vm.IsLightWatchRunning) vm.StartLightGateDiagnosticSession();
        else vm.StopLightGateDiagnosticSession();

        EventHandler? layoutHandler = null;
        layoutHandler = (_, _) =>
        {
            if (!TryBind(window, vm)) return;
            window.LayoutUpdated -= layoutHandler;
        };
        window.LayoutUpdated += layoutHandler;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            if (TryBind(window, vm)) window.LayoutUpdated -= layoutHandler;
        }), System.Windows.Threading.DispatcherPriority.ContextIdle);
    }

    private static bool TryBind(MainWindow window, MainViewModel vm)
    {
        var readiness = FindText(window, "فقط تشخیصی · گیت اجرایی خاموش است");
        if (readiness is null) return false;
        readiness.SetBinding(TextBlock.TextProperty,
            new Binding(nameof(MainViewModel.LightGateDiagnosticDisplay)) { Source = vm });
        readiness.SetBinding(FrameworkElement.ToolTipProperty,
            new Binding(nameof(MainViewModel.LightGateDiagnosticReasonDisplay)) { Source = vm });

        var section = FindStatusSection(window);
        if (section is null) return false;
        if (section.Children.OfType<Border>().Any(x => Equals(x.Tag, "authorization-diagnostics"))) return true;
        section.Children.Insert(Math.Min(2, section.Children.Count), BuildAuthorizationCard(vm));
        return true;
    }

    private static Border BuildAuthorizationCard(MainViewModel vm)
    {
        var body = new StackPanel();
        body.Children.Add(Text("مجوز تشخیصی — بدون اجرا", 15, "#F5F7FA"));
        body.Children.Add(Text(
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

        var arm = ActionButton("Arm تشخیصی");
        arm.Click += (_, _) => vm.ArmLightAuthorizationDiagnostic();
        row.Children.Add(arm);
        var issue = ActionButton("صدور Permit");
        issue.Click += (_, _) => vm.IssueLightAuthorizationDiagnosticPermit();
        row.Children.Add(issue);
        var consume = ActionButton("مصرف بدون اجرا");
        consume.Click += (_, _) => vm.ConsumeLightAuthorizationDiagnosticPermit();
        row.Children.Add(consume);
        var revoke = ActionButton("ابطال");
        revoke.Click += (_, _) => vm.RevokeLightAuthorizationDiagnostic();
        row.Children.Add(revoke);
        body.Children.Add(row);

        var state = Text("", 13, "#D9DEE7");
        state.SetBinding(TextBlock.TextProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticDisplay)) { Source = vm });
        state.SetBinding(FrameworkElement.ToolTipProperty,
            new Binding(nameof(MainViewModel.LightAuthorizationDiagnosticReasonDisplay)) { Source = vm });
        body.Children.Add(state);

        return new Border
        {
            Tag = "authorization-diagnostics", Child = body,
            Background = Brush("#22262D"), BorderBrush = Brush("#4A5360"),
            BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8),
            Padding = new Thickness(14), Margin = new Thickness(4, 0, 4, 10),
        };
    }

    private static Button ActionButton(string label) => new()
    {
        Content = label, Padding = new Thickness(12, 6, 12, 6), Margin = new Thickness(3),
        Background = Brush("#333A45"), Foreground = Brush("#F5F7FA"), MinHeight = 34,
    };

    private static TextBlock Text(string value, double size, string color) => new()
    {
        Text = value, FontSize = size, Foreground = Brush(color),
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

    private static TextBlock? FindText(DependencyObject root, string text)
    {
        if (root is TextBlock rootBlock && rootBlock.Text == text) return rootBlock;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var found = FindText(VisualTreeHelper.GetChild(root, i), text);
            if (found is not null) return found;
        }
        return null;
    }

    private static SolidColorBrush Brush(string value)
        => new((Color)ColorConverter.ConvertFromString(value));
}
