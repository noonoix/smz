using System;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class MouseStopReliabilityTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var code = PicoFirmwareExporter.BuildCodePy(Array.Empty<PicoFirmwareExporter.LightState>(), "mouse-stop-test");
        if (!code.Contains("FAST_MOUSE_PREFIXES", StringComparison.Ordinal)
            || code.Contains("MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\"", StringComparison.Ordinal))
            throw new Exception("MCLICK is still fire-and-ack");
        if (!code.Contains("forward_to_arm(line, _mclick_timeout(line))", StringComparison.Ordinal))
            throw new Exception("MCLICK does not wait for physical release");
        if (!code.Contains("if line == _last_hostusb_event[0]", StringComparison.Ordinal))
            throw new Exception("HOSTUSB deduplication missing");
    }
}
