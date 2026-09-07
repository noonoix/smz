using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;
using Ams.UI.ViewModels;

namespace Ams.UI.Converters;

/// <summary>Maps the board connection state to its status-chip brush (section 13.6: icon + text, never color alone).</summary>
public sealed class ConnectionBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        var key = value switch
        {
            ConnectionState.Connected => "OkBrush",
            ConnectionState.Handshaking => "WarnBrush",
            _ => "StepDelayBrush", // disconnected → neutral grey
        };
        return System.Windows.Application.Current.Resources[key] as System.Windows.Media.Brush ?? System.Windows.Media.Brushes.Gray;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
