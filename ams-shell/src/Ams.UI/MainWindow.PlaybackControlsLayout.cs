using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Keeps Run/Pause/Resume/Stop visible even when the connection/status content is wide.
/// The XAML DockPanel used to measure the left status stack first, so at the minimum
/// window width it consumed the remaining space and clipped the playback stack entirely.
/// Reserving the right-docked playback stack first makes the controls non-negotiable;
/// the informational status content is the part allowed to clip.
/// </summary>
internal static class PlaybackControlsLayoutBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "PlaybackControlsLayoutInstalled", typeof(bool), typeof(PlaybackControlsLayoutBootstrap),
        new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.DataContext is not MainViewModel vm) return;

        vm.InstallPlaybackStateGuard();

        var runButton = FindDescendants<System.Windows.Controls.Primitives.ButtonBase>(window)
            .FirstOrDefault(button => ReferenceEquals(button.Command, vm.RunCommand));
        if (runButton?.Parent is not StackPanel playback || playback.Parent is not DockPanel host) return;

        window.SetValue(InstalledProperty, true);
        host.Children.Remove(playback);
        host.Children.Insert(0, playback); // DockPanel measures children in declaration order.
        DockPanel.SetDock(playback, Dock.Right);
        playback.HorizontalAlignment = HorizontalAlignment.Right;
        playback.MinWidth = 250;
    }

    private static IEnumerable<T> FindDescendants<T>(DependencyObject root) where T : DependencyObject
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is T hit) yield return hit;
            foreach (var nested in FindDescendants<T>(child)) yield return nested;
        }
    }
}
