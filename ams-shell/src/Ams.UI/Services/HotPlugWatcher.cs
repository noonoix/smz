// v0.9.52 - hot-plug watcher. Before this, a board plugged in after the app started was
// invisible until a full restart: the port list was only read on demand and Connect was
// always manual, so the status light stayed grey. The watcher polls the live serial-port
// set, reports arrivals/departures, refreshes the port picker and (when idle) connects by
// itself, so plugging the board in lights it up within about a second.
// All logic here is pure and covered by TestRunner step 52; only the timer lives in the VM.
using System;
using System.Collections.Generic;

namespace Ams.UI.Services;

public static class HotPlugWatcher
{
    /// <summary>Poll interval. Fast enough to feel instant, slow enough to cost nothing.</summary>
    public const int PollMs = 1500;

    /// <summary>Numeric COM ordering so COM9 sorts before COM10 (string sort does not).</summary>
    public static int PortNumber(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return 0;
        var t = name.Trim();
        if (t.Length < 4) return 0;
        if (!t.StartsWith("COM", StringComparison.OrdinalIgnoreCase)) return 0;
        return int.TryParse(t.Substring(3), out var n) && n > 0 ? n : 0;
    }

    /// <summary>Live serial ports, de-duplicated and ordered. Never throws.</summary>
    public static List<string> CurrentPorts()
    {
        var list = new List<string>();
        try
        {
            foreach (var raw in System.IO.Ports.SerialPort.GetPortNames())
            {
                var t = (raw ?? string.Empty).Trim();
                if (t.Length > 0 && !list.Contains(t)) list.Add(t);
            }
        }
        catch { return new List<string>(); }
        list.Sort(static (a, b) =>
        {
            var na = PortNumber(a);
            var nb = PortNumber(b);
            if (na != nb && na > 0 && nb > 0) return na.CompareTo(nb);
            return string.Compare(a, b, StringComparison.OrdinalIgnoreCase);
        });
        return list;
    }

    /// <summary>Entries present in <paramref name="after"/> but not in <paramref name="before"/>.</summary>
    public static List<string> Added(IEnumerable<string>? before, IEnumerable<string>? after)
    {
        var known = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (before is not null) foreach (var b in before) known.Add(b);
        var result = new List<string>();
        if (after is null) return result;
        foreach (var a in after)
            if (!known.Contains(a) && !result.Contains(a)) result.Add(a);
        return result;
    }

    /// <summary>Auto-connect only when the app is idle and something actually arrived.</summary>
    public static bool ShouldAutoConnect(bool disconnected, bool busy, int arrivedCount, bool enabled)
        => enabled && disconnected && !busy && arrivedCount > 0;

    /// <summary>One Persian log line for a port-set change; empty when nothing changed.</summary>
    public static string DescribeChange(IReadOnlyList<string>? arrived, IReadOnlyList<string>? left)
    {
        var parts = new List<string>();
        if (arrived is not null && arrived.Count > 0)
            parts.Add("پورت تازه: " + string.Join(", ", arrived));
        if (left is not null && left.Count > 0)
            parts.Add("قطع شد: " + string.Join(", ", left));
        return parts.Count == 0 ? string.Empty : string.Join(" · ", parts);
    }
}
