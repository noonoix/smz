using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Routes the existing Copy/Paste UI and shortcuts to the Windows clipboard commands.</summary>
internal static class SystemClipboardCommandRouting
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "SystemClipboardRoutingInstalled", typeof(bool), typeof(SystemClipboardCommandRouting), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);

        foreach (var binding in window.InputBindings.OfType<KeyBinding>())
        {
            if (binding.Key == Key.C && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.CopySystemClipboardCommand;
            else if (binding.Key == Key.V && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.PasteSystemClipboardCommand;
        }

        foreach (var item in Descendants<MenuItem>(window))
        {
            var header = item.Header?.ToString() ?? string.Empty;
            if (header is "_Copy" or "Copy") item.Command = vm.CopySystemClipboardCommand;
            else if (header is "_Paste" or "Paste") item.Command = vm.PasteSystemClipboardCommand;
        }
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
