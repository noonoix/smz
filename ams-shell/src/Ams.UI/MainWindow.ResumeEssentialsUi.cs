using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Ams.UI.ViewModels;

namespace Ams.UI;

/// <summary>Accessible card for selecting the resume-only Random Package pre-pass.</summary>
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

        var panel = new StackPanel { FlowDirection = FlowDirection.RightToLeft };
        var head = new Grid();
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var title = AutoCycleUiKit.Title("بسته‌ی ضروری پس از بازگشت");
        var badge = AutoCycleUiKit.Badge("Resume Essentials", AutoCycleUiKit.Success, AutoCycleUiKit.Raised);
        Grid.SetColumn(title, 0);
        Grid.SetColumn(badge, 1);
        head.Children.Add(title);
        head.Children.Add(badge);
        panel.Children.Add(head);
        panel.Children.Add(AutoCycleUiKit.Helper(
            "یک Random Package را انتخاب و ثبت کن. پس از Auto Resume، تمام آیتم‌های فعال آن یک‌بار با ترتیب تصادفی اجرا می‌شوند."));

        var row = new Grid { FlowDirection = FlowDirection.RightToLeft };
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) });
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(150) });
        var mark = AutoCycleUiKit.Action("ثبت بسته‌ی انتخاب‌شده", true);
        mark.Margin = new Thickness(0);
        mark.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.MarkResumeEssentialsCommand)));
        var clear = AutoCycleUiKit.Action("پاک‌کردن انتخاب");
        clear.Margin = new Thickness(0);
        clear.SetBinding(Button.CommandProperty, new Binding(nameof(MainViewModel.ClearResumeEssentialsCommand)));
        Grid.SetColumn(mark, 0);
        Grid.SetColumn(clear, 2);
        row.Children.Add(mark);
        row.Children.Add(clear);
        panel.Children.Add(row);

        body.Children.Add(AutoCycleUiKit.Card(AutoCycleUiKit.EssentialsTag, panel));
        AutoCycleUiKit.Reorder(body);
    }
}
