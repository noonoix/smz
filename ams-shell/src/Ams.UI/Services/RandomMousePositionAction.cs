using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// The action-capable random-mouse primitive. This is intentionally separate from
/// <c>randomMousePosition</c>: existing .amsj files keep their old semantics, while
/// callers that opt into this primitive get one destination, one continuous human
/// path, and an action only after the path has settled.
/// </summary>
public static class RandomMousePositionAction
{
    public enum ActionKind { MoveOnly, LeftClick, RightClick, Scroll }

    public readonly record struct Region(int X, int Y, int Width, int Height)
    {
        public Region Normalize()
            => new(X, Y, Math.Max(1, Width), Math.Max(1, Height));
    }

    public readonly record struct Selection(Point Start, Point Destination, HumanMouse.Plan Plan);

    /// <summary>Selects the destination exactly once inside the normalized region and
    /// plans from the supplied real cursor position. The source is never replaced by
    /// the region origin.</summary>
    public static Selection Select(Point realCursor, Region region, HumanMouse.Config config,
                                   HumanMouse.PausePlanner pauses, Random rng,
                                   int screenWidth, int screenHeight)
    {
        var r = region.Normalize();
        int x = r.X + rng.Next(r.Width);
        int y = r.Y + rng.Next(r.Height);
        var plan = HumanMouse.PlanMove(realCursor.X, realCursor.Y, x, y, config, pauses, rng,
                                        screenWidth, screenHeight);
        return new Selection(realCursor, new Point(x, y), plan);
    }

    public static string ActionCommand(ActionKind action, int scrollDelta = -1)
        => action switch
        {
            ActionKind.LeftClick => "MCLICK|left,1",
            ActionKind.RightClick => "MCLICK|right,1",
            ActionKind.Scroll => $"MWHEEL|{scrollDelta}",
            _ => "",
        };

    /// <summary>Executes the already-planned selection. The final waypoint is asserted
    /// before the action is sent. If send_path is unavailable, fallback control points
    /// continue from the last point sent; they never replay the original path.</summary>
    public static async Task<Point> ExecuteAsync(IBoardBridge bridge, Selection selection,
                                                  ActionKind action, int scrollDelta = -1,
                                                  CancellationToken ct = default)
    {
        var plan = selection.Plan;
        if (plan.Waypoints.Count == 0)
            throw new InvalidOperationException("Human mouse planner returned no waypoints.");

        var points = plan.Waypoints.Select(w => (w.X, w.Y, w.DelayMs)).ToList();
        try
        {
            await bridge.SendPathAsync(points, ct);
        }
        catch (InvalidOperationException ex) when (ex.Message.Contains("unknown op", StringComparison.OrdinalIgnoreCase))
        {
            // The fallback starts at the actual source represented by the selection and
            // then advances its local position after every successful command.
            var current = selection.Start;
            foreach (var p in plan.ControlPoints)
            {
                ct.ThrowIfCancellationRequested();
                await bridge.SendAsync($"MMOVE|{p.X},{p.Y},abs,1", null, ct);
                current = new Point(p.X, p.Y);
                if (p.DelayMs > 0) await Task.Delay(p.DelayMs, ct);
            }
            if (current != selection.Destination)
            {
                await bridge.SendAsync($"MMOVE|{selection.Destination.X},{selection.Destination.Y},abs,1", null, ct);
                current = selection.Destination;
            }
        }

        var last = plan.Waypoints[^1];
        if (last.X != selection.Destination.X || last.Y != selection.Destination.Y)
            throw new InvalidOperationException("Human mouse plan did not end at its selected destination.");

        var command = ActionCommand(action, scrollDelta);
        if (command.Length > 0) await bridge.SendAsync(command, null, ct);
        return selection.Destination;
    }
}
