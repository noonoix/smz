namespace Ams.UI.Services;

public sealed record LightCalibrationSuggestion(
    double CenterLux,
    double ToleranceLux,
    double MinimumLux,
    double MaximumLux,
    int SampleCount);

/// <summary>Pure proposal logic. It never writes a profile; applying and saving require explicit user actions.</summary>
public static class LightCalibrationSuggester
{
    public static LightCalibrationSuggestion Suggest(IEnumerable<double> samples)
    {
        var values = samples.Where(x => double.IsFinite(x) && x >= 0).OrderBy(x => x).ToArray();
        if (values.Length == 0) throw new ArgumentException("At least one valid Lux sample is required.", nameof(samples));
        var middle = values.Length / 2;
        var median = values.Length % 2 == 0 ? (values[middle - 1] + values[middle]) / 2 : values[middle];
        var minimum = values[0];
        var maximum = values[^1];
        var tolerance = Math.Max(0.5, Math.Ceiling((((maximum - minimum) / 2) + 0.5) * 10) / 10);
        return new LightCalibrationSuggestion(median, tolerance, minimum, maximum, values.Length);
    }
}
