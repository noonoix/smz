using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Prevents a failed TextBox-to-number conversion (for example an empty field)
/// from silently saving the previous model value.
/// </summary>
internal static class LightProfileEditorValidationBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(Button), Button.ClickEvent,
            new RoutedEventHandler(OnButtonClick), true);

    private static void OnButtonClick(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Content: string label } button
            || label != "ذخیره پروفایل‌ها"
            || Window.GetWindow(button) is not MainWindow window
            || window.DataContext is not MainViewModel vm) return;

        UpdateNumericEditors(window);
        if (!HasValidationError(window)) return;

        e.Handled = true;
        vm.ReportLightProfileEditorValidationError();
    }

    private static void UpdateNumericEditors(DependencyObject root)
    {
        if (root is TextBox box)
            box.GetBindingExpression(TextBox.TextProperty)?.UpdateSource();
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            UpdateNumericEditors(VisualTreeHelper.GetChild(root, i));
    }

    private static bool HasValidationError(DependencyObject root)
    {
        if (Validation.GetHasError(root)) return true;
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
            if (HasValidationError(VisualTreeHelper.GetChild(root, i))) return true;
        return false;
    }
}
