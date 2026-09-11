using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Adds Resume Essentials controls below the automatic-cycle fields.</summary>
internal static class ResumeEssentialsUiBootstrap
{
    private static readonly DependencyProperty InstalledProperty = DependencyProperty.RegisterAttached(
        "ResumeEssentialsUiInstalled", typeof(bool), typeof(ResumeEssentialsUiBootstrap), new PropertyMetadata(false));

    [ModuleInitializer]
    internal static void Initialize()
        => EventManager.RegisterClassHandler(typeof(MainWindow), FrameworkElement.LoadedEvent,
            new RoutedEventHandler(OnLoaded), true);

    private static void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (sender is not MainWindow window || window.GetValue(InstalledProperty) is true) return;
        if (window.FindName("PlayOptBody") is not StackPanel body) return;
        window.SetValue(InstalledProperty, true);

        var panel = new StackPanel
        {
            FlowDirection = FlowDirection.RightToLeft,
            Margin = new Thickness(0, 8, 0, 0),
        };
        panel.Children.Add(new TextBlock
        {
            Text = "Resume Essentials",
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 0, 0, 4),
        });
        panel.Children.Add(new TextBlock
        {
            Text = "یک Random Package را انتخاب کن و آن را به‌عنوان بسته‌ی ضروری بازگشت ثبت کن. حالت آن همیشه Shuffle All است.",
            TextWrapping = TextWrapping.Wrap,
            FontSize = 11,
            Opacity = 0.78,
            Margin = new Thickness(0, 0, 0, 5),
        });

        var row = new StackPanel { Orientation = Orientation.Horizontal };
        var mark = new Button { Content = "ثبت بسته‌ی انتخاب‌شده", Padding = new Thickness(8, 3, 8, 3) };
        mark.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.MarkResumeEssentialsCommand)));
        var clear = new Button
        {
            Content = "پاک‌کردن",
            Padding = new Thickness(8, 3, 8, 3),
            Margin = new Thickness(6, 0, 0, 0),
        };
        clear.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.ClearResumeEssentialsCommand)));
        row.Children.Add(mark);
        row.Children.Add(clear);
        panel.Children.Add(row);
        body.Children.Add(panel);
    }
}
