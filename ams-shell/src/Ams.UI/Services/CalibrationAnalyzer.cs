using System;
using System.Collections.Generic;

namespace Ams.UI.Services;

/// <summary>
/// v0.9.23 — "Learn from my hand" math: derives a personal typing cadence and mouse
/// speed range from a short self-recording made inside the CalibrationWindow.
///
/// Recorded human baseline this is calibrated against (the user's own 57.8 s recording,
/// 1,255 mouse samples / 149 keys): mouse velocity median ≈ 140 px/s, p10 ≈ 63,
/// p90 ≈ 236, p99 ≈ 452; typing median ≈ 204 ms between keys; zero teleports.
///
/// Pure logic (no WPF) so TestRunner can drive it directly.
/// </summary>
public static class CalibrationAnalyzer
{
    /// <summary>The measured human profile. Ranges are robust (p25–p85) so one slow
    /// glance-away or one flick never widens them.</summary>
    public sealed record CalibrationResult(
        int KeyMinMs, int KeyMaxMs, double KeyMedianMs, int KeySamples,
        int MouseMinPxPerSec, int MouseMaxPxPerSec, double MouseMedianPxPerSec, int MouseSamples);

    /// <summary>Nearest-rank percentile over an ASCENDING-sorted list.</summary>
    public static double Percentile(IReadOnlyList<double> sortedAsc, double p)
    {
        if (sortedAsc.Count == 0) return 0;
        p = Math.Clamp(p, 0, 100);
        int idx = (int)Math.Round((p / 100.0) * (sortedAsc.Count - 1));
        return sortedAsc[Math.Clamp(idx, 0, sortedAsc.Count - 1)];
    }

    /// <summary>
    /// Derives the personal ranges from raw samples.
    /// Typing: inter-key gaps inside [20..1500] ms (excludes long thinking pauses — those
    /// belong to the word/think machinery), then min = p25 / max = p85 clamped to [40..600].
    /// Mouse: instantaneous velocity for sample gaps in [4..120] ms, then min = p25 /
    /// max = p85 clamped to [150..2500].
    /// Returns null when there are too few samples to be meaningful (needs ≥12 key gaps
    /// and ≥40 velocity samples).
    /// </summary>
    public static CalibrationResult? Compute(
        IReadOnlyList<long> keyTicksMs,
        IReadOnlyList<(long TickMs, double X, double Y)> mouseSamples)
    {
        var gaps = new List<double>();
        for (int i = 1; i < keyTicksMs.Count; i++)
        {
            long g = keyTicksMs[i] - keyTicksMs[i - 1];
            if (g is >= 20 and <= 1500) gaps.Add(g);
        }

        var vels = new List<double>();
        for (int i = 1; i < mouseSamples.Count; i++)
        {
            double dt = mouseSamples[i].TickMs - mouseSamples[i - 1].TickMs;
            if (dt is < 4 or > 120) continue;   // jitter or a rest — not a movement sample
            double dx = mouseSamples[i].X - mouseSamples[i - 1].X;
            double dy = mouseSamples[i].Y - mouseSamples[i - 1].Y;
            double dist = Math.Sqrt(dx * dx + dy * dy);
            if (dist <= 0) continue;
            vels.Add(dist / dt * 1000.0);
        }

        if (gaps.Count < 12 || vels.Count < 40) return null;

        gaps.Sort();
        vels.Sort();
        int keyMin = (int)Math.Clamp(Math.Round(Percentile(gaps, 25)), 40, 600);
        int keyMax = (int)Math.Clamp(Math.Round(Percentile(gaps, 85)), keyMin, 600);
        int mMin = (int)Math.Clamp(Math.Round(Percentile(vels, 25)), 150, 2500);
        int mMax = (int)Math.Clamp(Math.Round(Percentile(vels, 85)), mMin, 2500);

        return new CalibrationResult(
            keyMin, keyMax, Percentile(gaps, 50), gaps.Count,
            mMin, mMax, Percentile(vels, 50), vels.Count);
    }
}
