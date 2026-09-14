using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

using WpfBrush = System.Windows.Media.Brush;
using WpfPanel = System.Windows.Controls.Panel;

namespace Ams.UI;

/// <summary>Turns the status footer into responsive, multi-row cards instead of one long line.</summary>
// The footer layout is intentionally assembled after XAML load so existing bindings remain intact.
internal static class FooterUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "FooterUiInstalled", typeof(bool), typeof(FooterUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.Content is not Grid root) return;
        var footer = root.Children.OfType<Border>()
            .FirstOrDefault(x => Grid.GetRow(x) == 3 && x.Child is DockPanel);
        if (footer?.Child is not DockPanel dock) return;
        window.SetValue(InstalledProperty, true);

        var connection = dock.Children.OfType<StackPanel>()
            .FirstOrDefault(x => DockPanel.GetDock(x) == Dock.Left);
        var actions = dock.Children.OfType<StackPanel>()
            .FirstOrDefault(x => DockPanel.GetDock(x) == Dock.Right);
        if (connection is null || actions is null) return;

        dock.Children.Clear();
        var layout = new Grid { FlowDirection = FlowDirection.RightToLeft };
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var connectionWrap = new WrapPanel
        {
            Orientation = Orientation.Horizontal,
            FlowDirection = FlowDirection.RightToLeft,
            VerticalAlignment = VerticalAlignment.Center,
        };
        MoveChildren(connection, connectionWrap);
        var copy = new Button { Content = "📋 کپی مشخصات اتصال", Padding = new Thickness(10, 3, 10, 3), Margin = new Thickness(8, 3, 4, 3), ToolTip = "کپی متن کامل وضعیت اتصال" };
        copy.Click += (_, _) =>
        {
  var text = string.Join(Environment.NewLine, connectionWrap.Children.OfType<TextBlock>().Select(x => x.Text).Where(x => !string.IsNullOrWhiteSpace(x)));
  if (!string.IsNullOrWhiteSpace(text)) Clipboard.SetText(text);
        };
        connectionWrap.Children.Add(copy);
        Grid.SetRow(connectionWrap, 0);
        layout.Children.Add(Card("بردها و اتصال", connectionWrap));

        var actionWrap = new WrapPanel
        {
            Orientation = Orientation.Horizontal,
            FlowDirection = FlowDirection.RightToLeft,
            HorizontalAlignment = HorizontalAlignment.Right,
        };
        MoveChildren(actions, actionWrap);
        Grid.SetRow(actionWrap, 1);
        layout.Children.Add(Card("کنترل اجرا", actionWrap));

        footer.Padding = new Thickness(8, 6, 8, 6);
        footer.Child = layout;
    }

    private static void MoveChildren(WpfPanel source, WpfPanel destination)
    {
        var children = source.Children.Cast<UIElement>().ToList();
        source.Children.Clear();
        foreach (var child in children)
        {
            if (child is FrameworkElement element)
            {
                element.Margin = new Thickness(4, 3, 4, 3);
                element.VerticalAlignment = VerticalAlignment.Center;
                if (element is TextBlock text)
                {
                    text.TextWrapping = TextWrapping.Wrap;
                    text.MaxWidth = 260;
                }
            }
            destination.Children.Add(child);
        }
    }

    private static Border Card(string title, UIElement content)
    {
        var panel = new StackPanel();
        panel.Children.Add(new TextBlock
        {
            Text = title,
            Foreground = System.Windows.Media.Brushes.LightGray,
            FontSize = 10,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(4, 0, 4, 2),
        });
        panel.Children.Add(content);
        return new Border
        {
            Background = TryBrush("BgElevatedBrush", new SolidColorBrush(System.Windows.Media.Color.FromRgb(45, 49, 58))),
            BorderBrush = TryBrush("BorderSubtleBrush", new SolidColorBrush(System.Windows.Media.Color.FromRgb(68, 74, 85))),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(6, 4, 6, 4),
            Margin = new Thickness(0, 2, 0, 2),
            Child = panel,
        };
    }

    private static WpfBrush TryBrush(string key, WpfBrush fallback)
        => System.Windows.Application.Current?.TryFindResource(key) as WpfBrush ?? fallback;
}
