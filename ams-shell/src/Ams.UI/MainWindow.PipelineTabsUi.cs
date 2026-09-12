using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Ams.UI.Models;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Fixed, non-closable browser-style tabs above the existing step editor.</summary>
internal static class PipelineTabsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "PipelineTabsUiInstalled", typeof(bool), typeof(PipelineTabsUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.FindName("StepsList") is not ListBox steps || steps.Parent is not Grid host) return;
        if (window.DataContext is not MainViewModel vm) return;
        window.SetValue(InstalledProperty, true);
        vm.InitializePipelineTabs();

        var existing = host.Children.Cast<UIElement>().ToList();
        host.RowDefinitions.Insert(0, new RowDefinition { Height = GridLength.Auto });
        foreach (var child in existing) Grid.SetRow(child, Grid.GetRow(child) + 1);

        var strip = new DockPanel
        {
            LastChildFill = true,
            Background = new SolidColorBrush(Color.FromRgb(31, 35, 40)),
            Margin = new Thickness(0, 0, 0, 4),
        };
        var tools = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        tools.Children.Add(ToolButton("جدید", vm.NewPipelineWorkspaceCommand));
        tools.Children.Add(ToolButton("بازکردن", vm.OpenPipelineWorkspaceCommand));
        tools.Children.Add(ToolButton("ذخیره", vm.SavePipelineWorkspaceCommand));
        DockPanel.SetDock(tools, Dock.Right);
        strip.Children.Add(tools);

        var tabs = new StackPanel { Orientation = Orientation.Horizontal, FlowDirection = FlowDirection.LeftToRight };
        var buttons = new List<Button>();
        foreach (var tab in vm.PipelineTabs)
        {
            var button = new Button
            {
                Content = tab.Title,
                Tag = tab,
                Padding = new Thickness(12, 7, 12, 7),
                Margin = new Thickness(0, 2, 3, 0),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand,
                ToolTip = tab.FileName,
            };
            button.Click += (_, _) =>
            {
                if (vm.SwitchPipelineCommand.CanExecute(tab)) vm.SwitchPipelineCommand.Execute(tab);
                Paint(buttons, vm.ActivePipelineTab);
            };
            buttons.Add(button);
            tabs.Children.Add(button);
        }
        strip.Children.Add(tabs);
        Grid.SetRow(strip, 0);
        host.Children.Add(strip);
        Paint(buttons, vm.ActivePipelineTab);

        for (var i = 0; i < vm.PipelineTabs.Count && i < 9; i++)
            window.InputBindings.Add(new KeyBinding(vm.SwitchPipelineCommand,
                new KeyGesture(Key.D1 + i, ModifierKeys.Control)) { CommandParameter = vm.PipelineTabs[i] });
    }

    private static Button ToolButton(string title, ICommand command) => new()
    {
        Content = title,
        Command = command,
        Padding = new Thickness(9, 5, 9, 5),
        Margin = new Thickness(3, 3, 0, 3),
        MinWidth = 64,
    };

    private static void Paint(IEnumerable<Button> buttons, PipelineTabDocument? active)
    {
        foreach (var button in buttons)
        {
            var selected = ReferenceEquals(button.Tag, active);
            button.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(selected ? "#5E9FE8" : "#333740"));
            button.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(selected ? "#10151C" : "#F5F7FA"));
            button.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(selected ? "#5E9FE8" : "#444A55"));
            button.FontWeight = selected ? FontWeights.SemiBold : FontWeights.Normal;
        }
    }
}
