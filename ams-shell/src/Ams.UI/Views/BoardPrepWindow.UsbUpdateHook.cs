using System.Windows;

namespace Ams.UI.Views;

public partial class BoardPrepWindow
{
    // This class handler keeps the feature present even in older release branches where
    // the generated constructor patch has not yet been applied. The initializer itself is
    // idempotent, so it is safe when both paths are present.
    static BoardPrepWindow()
    {
        EventManager.RegisterClassHandler(
            typeof(BoardPrepWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler((sender, _) =>
            {
                if (sender is BoardPrepWindow window) window.InitializeUsbUpdatePanel();
            }));
    }
}
