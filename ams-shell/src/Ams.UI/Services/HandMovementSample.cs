using System.Diagnostics;
using System.Drawing;
using System.Globalization;

namespace Ams.UI.Services;

/// <summary>Captures only cursor deltas/timing. No keyboard, button, window title, text or secret data is observed.</summary>
public static class HandMovementSample
{
    public const int CaptureDurationMs = 10_000;
    public const int CaptureIntervalMs = 16;
    // One shared replay budget keeps desktop, generated scripts, and bare-Pico plans identical.
    // More points materially increase the Pico parser heap without adding useful hand detail.
    public const int ReplaySegmentLimit = 48;
    public readonly record struct Segment(int DelayMs, int Dx, int Dy);
    public sealed record Sample(int DurationMs, Point Start, Point End, IReadOnlyList<Segment> Segments);

    // The v1 payload is intentionally limited to cursor coordinates, relative deltas, and timing.
    public static async Task<Sample?> CaptureAsync(CancellationToken ct = default)
    {
        var start = System.Windows.Forms.Cursor.Position;
        var previous = start;
        var lastChangeMs = 0;
        var segments = new List<Segment>();
        var sw = Stopwatch.StartNew();
        while (sw.ElapsedMilliseconds < CaptureDurationMs)
        {
            ct.ThrowIfCancellationRequested();
            await Task.Delay(CaptureIntervalMs, ct);
            var now = System.Windows.Forms.Cursor.Position;
            int elapsed = (int)Math.Min(CaptureDurationMs, sw.ElapsedMilliseconds);
            int dx = now.X - previous.X, dy = now.Y - previous.Y;
            if (dx != 0 || dy != 0)
            {
                segments.Add(new Segment(Math.Max(1, elapsed - lastChangeMs), dx, dy));
                previous = now;
                lastChangeMs = elapsed;
            }
        }
        if (segments.Count == 0) return null;
        int trailing = Math.Max(1, CaptureDurationMs - lastChangeMs);
        segments.Add(new Segment(trailing, 0, 0));
        return new Sample(CaptureDurationMs, start, previous, Compact(segments, 240));
    }

    public static string Encode(Sample sample)
    {
        var parts = sample.Segments.Select(s => string.Create(CultureInfo.InvariantCulture, $"{s.DelayMs},{s.Dx},{s.Dy}"));
        return string.Create(CultureInfo.InvariantCulture,
            $"v1|{sample.DurationMs}|{sample.Start.X},{sample.Start.Y}|{sample.End.X},{sample.End.Y}|{string.Join(';', parts)}");
    }

    public static bool TryDecode(string? text, out Sample sample)
    {
        sample = new Sample(0, default, default, Array.Empty<Segment>());
        if (string.IsNullOrWhiteSpace(text)) return false;
        var fields = text.Split('|');
        if (fields.Length != 5 || fields[0] != "v1" || !int.TryParse(fields[1], out int duration)
            || duration is < 1 or > 60_000 || !TryPoint(fields[2], out var start) || !TryPoint(fields[3], out var end)) return false;
        var segments = new List<Segment>();
        foreach (var token in fields[4].Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            var p = token.Split(',');
            if (p.Length != 3 || !int.TryParse(p[0], out int dt) || !int.TryParse(p[1], out int dx) || !int.TryParse(p[2], out int dy)
                || dt is < 1 or > 60_000 || Math.Abs(dx) > 8192 || Math.Abs(dy) > 8192) return false;
            segments.Add(new Segment(dt, dx, dy));
        }
        if (segments.Count == 0 || segments.Count > 2000) return false;
        sample = new Sample(duration, start, end, segments);
        return true;
    }

    public static IReadOnlyList<Segment> Compact(IReadOnlyList<Segment> source, int maxSegments)
    {
        if (source.Count <= maxSegments) return source.ToArray();
        var result = new List<Segment>(maxSegments);
        for (int bucket = 0; bucket < maxSegments; bucket++)
        {
            int lo = bucket * source.Count / maxSegments;
            int hi = (bucket + 1) * source.Count / maxSegments;
            int dt = 0, dx = 0, dy = 0;
            for (int i = lo; i < hi; i++) { dt += source[i].DelayMs; dx += source[i].Dx; dy += source[i].Dy; }
            result.Add(new Segment(Math.Max(1, dt), dx, dy));
        }
        return result;
    }

    /// <summary>
    /// The recorded deltas are the authoritative payload. Start/End are capture metadata only;
    /// using their difference would let a malformed legacy payload describe a different move.
    /// </summary>
    public static Point Displacement(Sample sample)
    {
        int x = 0, y = 0;
        foreach (var segment in sample.Segments) { x += segment.Dx; y += segment.Dy; }
        return new Point(x, y);
    }

    private static bool TryPoint(string text, out Point point)
    {
        point = default; var p = text.Split(',');
        if (p.Length != 2 || !int.TryParse(p[0], out int x) || !int.TryParse(p[1], out int y)) return false;
        point = new Point(x, y); return true;
    }
}
