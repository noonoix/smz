using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// The shell originally kept the legacy Save/New/Open commands on the File menu and Ctrl+S.
/// Those commands operate on the visible Steps collection only, so they can persist just the
/// active pipeline tab. Route the file commands to the workspace-aware commands once the shell
/// is loaded; the five tab trees are then captured and serialized together.
/// </summary>
internal static class PipelineFileCommandRouting
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "PipelineFileCommandRoutingInstalled", typeof(bool), typeof(PipelineFileCommandRouting), new PropertyMetadata(false));

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
            if (binding.Key == Key.S && binding.Modifiers == ModifierKeys.Control)
                binding.Command = vm.SavePipelineWorkspaceCommand;
        }

        foreach (var item in Descendants<MenuItem>(window))
        {
            var header = item.Header?.ToString() ?? string.Empty;
            switch (header)
            {
                case "_New Script":
                    item.Command = vm.NewPipelineWorkspaceCommand;
                    break;
                case "_Open…":
                    item.Command = vm.OpenPipelineWorkspaceCommand;
                    break;
                case "_Save":
                    item.Command = vm.SavePipelineWorkspaceCommand;
                    break;
                case "Save _As…":
                    item.Command = vm.SavePipelineWorkspaceAsCommand;
                    break;
            }
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
