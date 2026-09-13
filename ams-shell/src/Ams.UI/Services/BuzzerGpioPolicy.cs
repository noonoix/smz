using System;
namespace Ams.UI.Services;
public static class BuzzerGpioPolicy
{
    private static readonly string[] Pins={"GP5","GP6","GP7","GP8","GP9","GP10","GP11","GP12","GP13","GP14","GP15","GP18","GP19","GP22","GP26","GP27","GP28"};
    public static IReadOnlyList<string> AllowedPins=>Pins;
    public static string NormalizeOrDefault(string? value)=>TryValidate(value,out var pin,out _)?pin:"GP6";
    public static bool TryValidate(string? value,out string pin,out string error)
    {
        pin=(value??"").Trim().ToUpperInvariant();
        if(pin.StartsWith("BOARD.",StringComparison.Ordinal))pin=pin[6..];
        if(pin is "GP3" or "GP4" or "GP16" or "GP17" or "GP20" or "GP21"){error=pin+" is reserved by the board contract.";return false;}
        if(!Pins.Contains(pin,StringComparer.Ordinal)){error=pin+" is not an allowed free PWM-capable Pico pin.";return false;}
        error="";return true;
    }
    public static string Require(string? value){if(TryValidate(value,out var pin,out var error))return pin;throw new InvalidOperationException("خروجی متوقف شد: "+error);}
}
