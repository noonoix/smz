using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Routes all step-tree clipboard gestures and menus to one Windows clipboard contract.</summary>
internal static class SystemClipboardCommandRouting
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "SystemClipboardRoutingInstalled", typeof(bool), typeof(SystemClipboardCommandRouting), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
    {
        EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);
        // ContextMenu lives in a separate popup tree, so a MainWindow descendant walk cannot
        // reach its Cut/Copy/Paste items. Route each MenuItem when its popup is loaded too.
        EventManager.RegisterClassHandler(typeof(MenuItem), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnMenuItemLoaded), true);
    }

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);
        RouteInputBindings(window, vm);
        foreach (var item in Descendants<MenuItem>(window)) RouteMenuItem(item, vm);
    }

    private static void OnMenuItemLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MenuItem item) return;
        var vm = ResolveViewModel(item);
        if (vm is not null) RouteMenuItem(item, vm);
    }

    private static void RouteInputBindings(MainWindow window, MainViewModel vm)
    {
        foreach (var binding in window.InputBindings.OfType<KeyBinding>())
        {
            if (binding.Key == Key.X && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.CutSystemClipboardCommand;
            else if (binding.Key == Key.C && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.CopySystemClipboardCommand;
            else if (binding.Key == Key.V && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.PasteSystemClipboardCommand;
        }
    }

    private static void RouteMenuItem(MenuItem item, MainViewModel vm)
    {
        var header = item.Header?.ToString()?.TrimStart('_') ?? string.Empty;
        if (header is "Cut") item.Command = vm.CutSystemClipboardCommand;
        else if (header is "Copy") item.Command = vm.CopySystemClipboardCommand;
        else if (header is "Paste") item.Command = vm.PasteSystemClipboardCommand;
    }

    private static MainViewModel? ResolveViewModel(MenuItem item)
    {
        if (item.DataContext is MainViewModel direct) return direct;
        for (DependencyObject? p = item; p is not null; p = LogicalTreeHelper.GetParent(p))
            if (p is FrameworkElement fe && fe.DataContext is MainViewModel inherited) return inherited;

        for (DependencyObject? p = item; p is not null; p = LogicalTreeHelper.GetParent(p))
        {
            if (p is not ContextMenu menu) continue;
            return (menu.PlacementTarget as FrameworkElement)?.DataContext as MainViewModel;
        }
        return null;
    }

    private static IEnumerable<T> Descendants<T>(DependencyObject root) where T : DependencyObject
    {
        foreach (var child in LogicalTreeHelper.GetChildren(root).OfType<DependencyObject>())
        {
            if (child is T match) yield return match;
            foreach (var nested in Descendants<T>(child)) yield return nested;
        }
    }
}
