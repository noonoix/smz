using System;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class HumanMouseDefaultsPhase1Tests
{
    [ModuleInitializer]
    internal static void Run()
    {
        if (HumanMouseDefaultsPolicy.CalibrateLegacyRange(300, 2000) != (400, 1500))
            throw new Exception("current factory mouse range was not human-calibrated");
        if (HumanMouseDefaultsPolicy.CalibrateLegacyRange(0, 2300) != (400, 1500))
            throw new Exception("legacy factory mouse range was not human-calibrated");
        if (HumanMouseDefaultsPolicy.CalibrateLegacyRange(250, 900) != (250, 900))
            throw new Exception("a custom mouse range was overwritten");
        if (HumanMouseDefaultsPolicy.SpeedMinPxPerSec >= HumanMouseDefaultsPolicy.SpeedMaxPxPerSec)
            throw new Exception("human mouse speed range is invalid");
    }
}
