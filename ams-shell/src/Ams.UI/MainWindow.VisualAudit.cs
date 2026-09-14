using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Ams.UI;

/// <summary>Final visual-audit pass for discoverability of the random-area mouse step.</summary>
internal static class VisualAuditBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not DependencyObject root) return;
        foreach (var item in Descendants(root).OfType<MenuItem>())
        {
            if (item.Header is string header && header.Contains("Random Mouse Position", StringComparison.OrdinalIgnoreCase))
                item.Header = "Move to Random Area";
        }
    }

    private static IEnumerable<DependencyObject> Descendants(DependencyObject root)
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            yield return child;
            foreach (var nested in Descendants(child)) yield return nested;
        }
    }
}
