using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Ams.UI.Models;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>
/// Handles conditional-block drops before the legacy row handler rejects If heads as atomic.
/// Ordinary row drops continue through the existing handler unchanged.
/// </summary>
internal static class ConditionalDragDropBootstrap
{
    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(ListBox), UIElement.DropEvent,
            new DragEventHandler(OnDrop), true);

    private static void OnDrop(object sender, System.Windows.DragEventArgs e)
    {
        if (sender is not ListBox list || list.Name != "StepsList") return;
        if (e.Data.GetData(typeof(StepNode)) is not StepNode node) return;
        if (list.DataContext is not MainViewModel vm || !vm.IsConditionalDragNode(node)) return;

        var item = FindRow(e.OriginalSource as DependencyObject);
        var target = (item?.DataContext as FlatStepRow)?.Node;
        string mode = "after";
        if (item is not null && target is not null)
        {
            var point = e.GetPosition(item);
            bool canInto = StepDefinitions.AcceptsChildren(target) || MainViewModel.IsElseMarkerRow(target);
            double edge = canInto ? 0.25 : 0.5;
            if (point.Y < item.ActualHeight * edge) mode = "before";
            else if (point.Y > item.ActualHeight * (1.0 - edge)) mode = "after";
            else mode = "into";
        }

        vm.MoveConditionalDragNode(node, target, mode);
        e.Handled = true;
    }

    private static ListBoxItem? FindRow(DependencyObject? value)
    {
        while (value is not null and not ListBoxItem)
            value = VisualTreeHelper.GetParent(value);
        return value as ListBoxItem;
    }
}
