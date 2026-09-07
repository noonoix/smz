using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.Models;

namespace Ams.UI.Converters;

/// <summary>Maps a step type key to its category color brush (design tokens, §13.3).</summary>
public sealed class StepTypeBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        var key = value is string type ? StepDefinitions.ColorKey(type) : "StepDelayBrush";
        return System.Windows.Application.Current.Resources[key] as System.Windows.Media.Brush ?? System.Windows.Media.Brushes.Gray;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
