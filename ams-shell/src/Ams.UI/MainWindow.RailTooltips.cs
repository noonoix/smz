using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Ams.UI;

/// <summary>Removes hover-description popups from the vertical quick-insert rail while
/// keeping tooltips elsewhere in the application unchanged.</summary>
public partial class MainWindow
{
    static MainWindow()
    {
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(MainWindowLoadedForRailTooltips));
    }

    private static void MainWindowLoadedForRailTooltips(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window) return;
        window.Dispatcher.BeginInvoke(new Action(() =>
        {
            foreach (var button in FindDescendants<Button>(window))
            {
                if (!IsVerticalRailButton(button)) continue;
                button.ToolTip = null;
                ToolTipService.SetIsEnabled(button, false);
            }
        }), System.Windows.Threading.DispatcherPriority.Loaded);
    }

    private static bool IsVerticalRailButton(Button button)
    {
        DependencyObject? current = button;
        while (current is not null)
        {
            if (current is Border border && border.Child is ScrollViewer)
            {
                var parent = VisualTreeHelper.GetParent(border);
                if (parent is Grid && Grid.GetRow(border) == 0 && Grid.GetColumn(border) == 0)
                    return true;
            }
            current = VisualTreeHelper.GetParent(current);
        }
        return false;
    }

    private static IEnumerable<T> FindDescendants<T>(DependencyObject root) where T : DependencyObject
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is T match) yield return match;
            foreach (var nested in FindDescendants<T>(child)) yield return nested;
        }
    }
}
