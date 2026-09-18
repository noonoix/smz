using System.Windows;
using Ams.UI.ViewModels;

namespace Ams.UI;

public partial class MainWindow
{
    private void OpenGuardStatusWindow_Click(object sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm)
        {
            vm.InitializeLightGuardAdapter();
            LightGuardStatusWindow.Show(this, vm);
        }
    }
}
