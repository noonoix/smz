using System;
using System.IO;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class AutoCycleMouseReliabilityTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var baseline = PicoFirmwareExporter.BuildCodePy(Array.Empty<PicoFirmwareExporter.LightState>(), "cycle-mouse-test");
        var manifest = Path.Combine(AppContext.BaseDirectory, "portable-runtime", "autocycle_h6_patch.json");
        var cycle = AutoCycleFirmwareBundle.PatchCode(baseline, manifest);
        if (!cycle.Contains("if head == \"MCLICK\":", StringComparison.Ordinal)
            || !cycle.Contains("forward_to_arm(line, _mclick_timeout(line))", StringComparison.Ordinal))
            throw new Exception("AutoCycle lost serialized MCLICK completion");
        if (!cycle.Contains("changed = (not _arm_host_usb_seen or state != _arm_host_usb_state)", StringComparison.Ordinal))
            throw new Exception("AutoCycle lost HOSTUSB state deduplication");
    }
}
