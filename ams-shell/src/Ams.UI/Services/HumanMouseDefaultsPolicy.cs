using System.Text;

namespace Ams.UI.Services;

/// <summary>
/// One-time v0.9.68 calibration from the user's 2026-09-13 hand trace.
/// The 10th–90th percentile of substantial hand-motion speed was approximately
/// 388–1478 px/s (median 962), so the rounded factory envelope is 400–1500 px/s.
/// Existing custom ranges are preserved; only the two historical factory pairs migrate.
/// A marker prevents a later deliberate choice of 300–2000 from being overwritten.
/// Per-step moveTime 0/0 remains the default so duration continues to scale with distance.
/// </summary>
public static class HumanMouseDefaultsPolicy
{
    public const int SpeedMinPxPerSec = 400;
    public const int SpeedMaxPxPerSec = 1500;

    private static string MarkerPath => Path.Combine(
        AppContext.BaseDirectory, ".human-mouse-defaults-20260913-v1");

    public static (int min, int max) CalibrateLegacyRange(int min, int max)
    {
        if ((min == 300 && max == 2000) || (min == 0 && max == 2300))
            return (SpeedMinPxPerSec, SpeedMaxPxPerSec);
        return (min, max);
    }

    public static bool ApplyOnce()
    {
        try
        {
            if (File.Exists(MarkerPath)) return false;

            var settings = AppSettings.Load();
            var calibrated = CalibrateLegacyRange(
                settings.MouseMoveSpeedMin, settings.MouseMoveSpeedMax);
            bool changed = calibrated != (settings.MouseMoveSpeedMin, settings.MouseMoveSpeedMax);
            if (changed)
            {
                settings.MouseMoveSpeedMin = calibrated.min;
                settings.MouseMoveSpeedMax = calibrated.max;
                settings.Save();
            }

            File.WriteAllText(MarkerPath,
                "Human mouse defaults calibrated to 400-1500 px/s from the 2026-09-13 hand trace.\n",
                Encoding.UTF8);
            return changed;
        }
        catch
        {
            // Read-only installs keep the historical settings rather than blocking startup.
            return false;
        }
    }
}
