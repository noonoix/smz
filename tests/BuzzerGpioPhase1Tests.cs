using System;
using System.Runtime.CompilerServices;
using Ams.UI.Services;
namespace Ams.Tests;
internal static class BuzzerGpioPhase1Tests
{
    [ModuleInitializer]
    internal static void Run()
    {
        if(BuzzerGpioPolicy.NormalizeOrDefault(null)!="GP6")throw new Exception("legacy buzzer default is not GP6");
        if(!BuzzerGpioPolicy.TryValidate("GP7",out var pin,out _)||pin!="GP7")throw new Exception("GP7 was not accepted");
        if(BuzzerGpioPolicy.TryValidate("GP20",out _,out _)||BuzzerGpioPolicy.TryValidate("GP3",out _,out _))throw new Exception("reserved buzzer pin was accepted");
        var code=PicoFirmwareExporter.BuildCodePy(Array.Empty<PicoFirmwareExporter.LightState>(),"phase1-test",buzzerGpio:"GP7");
        if(!code.Contains("PWMOut(board.GP7",StringComparison.Ordinal))throw new Exception("GP7 did not reach generated code.py");
        if(code.Contains("PWMOut(board.GP6",StringComparison.Ordinal))throw new Exception("generated code.py still contains hardcoded GP6 buzzer output");
    }
}
