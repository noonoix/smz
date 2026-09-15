using System.Runtime.CompilerServices;
using Ams.UI.Services;

internal static class LightCalibrationSuggestionContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var passed = 0;
        var failed = 0;
        void Check(bool condition, string name)
        {
            if (condition) { passed++; Console.WriteLine("PASS: " + name); }
            else { failed++; Console.WriteLine("FAIL: " + name); }
        }

        var proposal = LightCalibrationSuggester.Suggest(new[] { 24.8, 25.0, 25.2, 25.4, 90.0 });
        Check(proposal.CenterLux == 25.2,
            "calibration center uses the median and resists one bright outlier");
        Check(proposal.ToleranceLux == 33.1 && proposal.MinimumLux == 24.8 && proposal.MaximumLux == 90,
            "calibration proposal reports observed bounds and an explicit safety margin");
        Check(proposal.SampleCount == 5,
            "calibration proposal reports its valid sample count");

        var compact = LightCalibrationSuggester.Suggest(new[] { 10.0, 10.1, 10.2 });
        Check(compact.ToleranceLux == 0.6,
            "stable readings still receive a nonzero rounded margin");

        Console.WriteLine($"=== Light calibration suggestion results: {passed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Light calibration suggestion contract failed: {failed}");
    }
}
