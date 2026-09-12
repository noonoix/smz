using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Ams.UI;

/// <summary>Shared dark-dashboard primitives for the AutoCycle workflow.</summary>
internal static class AutoCycleUiKit
{
    internal const string ExportTag = "AutoCycle.Export";
    internal const string EssentialsTag = "AutoCycle.Essentials";
    internal const string ScheduleTag = "AutoCycle.Schedule";
    internal const string PlanStepTag = "AutoCycle.PlanStep";
    internal const string FirmwareStepTag = "AutoCycle.FirmwareStep";

    internal static readonly Brush Surface = MakeBrush("#292C33");
    internal static readonly Brush Raised = MakeBrush("#333740");
    internal static readonly Brush BorderBrush = MakeBrush("#444A55");
    internal static readonly Brush Primary = MakeBrush("#5E9FE8");
    internal static readonly Brush OnPrimary = MakeBrush("#10151C");
    internal static readonly Brush PrimarySoft = MakeBrush("#263A52");
    internal static readonly Brush Text = MakeBrush("#F5F7FA");
    internal static readonly Brush Muted = MakeBrush("#B5BBC5");
    internal static readonly Brush Success = MakeBrush("#72BC8F");

    private static SolidColorBrush MakeBrush(string value)
        => new((Color)ColorConverter.ConvertFromString(value));

    internal static Border Card(string tag, UIElement content)
        => new()
        {
            Tag = tag,
            Background = Surface,
            BorderBrush = BorderBrush,
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(10),
            Padding = new Thickness(16),
            Margin = new Thickness(0, 12, 0, 0),
            HorizontalAlignment = HorizontalAlignment.Stretch,
            Child = content,
        };

    internal static TextBlock Title(string text) => new()
    {
        Text = text,
        Foreground = Text,
        FontSize = 14,
        FontWeight = FontWeights.SemiBold,
        Margin = new Thickness(0, 0, 0, 4),
    };

    internal static TextBlock Helper(string text) => new()
    {
        Text = text,
        Foreground = Muted,
        FontSize = 12,
        LineHeight = 18,
        TextWrapping = TextWrapping.Wrap,
        Margin = new Thickness(0, 0, 0, 12),
    };

    internal static Button Action(string text, bool primary = false) => new()
    {
        Content = text,
        MinHeight = 44,
        Padding = new Thickness(14, 8, 14, 8),
        Margin = new Thickness(0, 6, 0, 0),
        HorizontalAlignment = HorizontalAlignment.Stretch,
        HorizontalContentAlignment = HorizontalAlignment.Center,
        FontWeight = FontWeights.SemiBold,
        Foreground = primary ? OnPrimary : Text,
        Background = primary ? Primary : Raised,
        BorderBrush = primary ? Primary : BorderBrush,
        BorderThickness = new Thickness(1),
    };

    internal static Border Badge(string text, Brush? foreground = null, Brush? background = null)
        => new()
        {
            Background = background ?? PrimarySoft,
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(8, 3, 8, 3),
            VerticalAlignment = VerticalAlignment.Center,
            Child = new TextBlock
            {
                Text = text,
                Foreground = foreground ?? Primary,
                FontSize = 11,
                FontWeight = FontWeights.SemiBold,
            },
        };

    internal static StackPanel EnsureExportCard(StackPanel body)
    {
        var existing = FindCard(body, ExportTag);
        if (existing?.Child is StackPanel found) return found;

        var panel = new StackPanel { FlowDirection = FlowDirection.RightToLeft };
        var head = new Grid();
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        head.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var title = Title("خروجی AutoCycle برای Pico");
        var badge = Badge("۲ مرحله");
        Grid.SetColumn(title, 0);
        Grid.SetColumn(badge, 1);
        head.Children.Add(title);
        head.Children.Add(badge);
        panel.Children.Add(head);
        panel.Children.Add(Helper("هر دو مرحله را در یک پوشه اجرا کن. خروجی‌های AutoCycle جای فایل‌های عادی Plan و Firmware را می‌گیرند."));
        body.Children.Add(Card(ExportTag, panel));
        Reorder(body);
        return panel;
    }

    internal static Border? FindCard(StackPanel body, string tag)
        => body.Children.OfType<Border>().FirstOrDefault(x => Equals(x.Tag, tag));

    internal static void ReorderExportSteps(StackPanel panel)
    {
        var steps = new[] { PlanStepTag, FirmwareStepTag }
            .Select(tag => panel.Children.OfType<Button>().FirstOrDefault(x => Equals(x.Tag, tag)))
            .Where(x => x is not null).Cast<Button>().ToList();
        foreach (var step in steps) panel.Children.Remove(step);
        foreach (var step in steps) panel.Children.Add(step);
    }

    internal static void Reorder(StackPanel body)
    {
        var cards = new[] { ExportTag, EssentialsTag, ScheduleTag }
            .Select(tag => FindCard(body, tag)).Where(x => x is not null).Cast<Border>().ToList();
        foreach (var card in cards) body.Children.Remove(card);
        foreach (var card in cards) body.Children.Add(card);
    }
}
