using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Independent action-capable random-mouse primitive. The legacy
/// <c>randomMousePosition</c> definition is not changed. This definition is
/// installed into the existing registry at module load, so old .amsj files and
/// their execution path remain unchanged.
/// </summary>
public static class RandomMousePositionAction
{
    public enum ActionKind { MoveOnly, LeftClick, RightClick, Scroll }

    public readonly record struct Region(int X, int Y, int Width, int Height)
    {
        public Region Normalize() => new(X, Y, Math.Max(1, Width), Math.Max(1, Height));
    }

    public readonly record struct Selection(Point Start, Point Destination, HumanMouse.Plan Plan);

    [ModuleInitializer]
    public static void InstallDefinition()
    {
        // The registry intentionally remains the single source of truth for the
        // generic dialog and step picker. This module initializer lets the new
        // step be additive without rewriting the large, stable registry file.
        var field = typeof(StepDefinitions).GetField("Defs", BindingFlags.NonPublic | BindingFlags.Static);
        if (field?.GetValue(null) is not Dictionary<string, StepDefinition> defs || defs.ContainsKey("randomMousePositionAction")) return;

        defs["randomMousePositionAction"] = new StepDefinition
        {
            Label = "Random Mouse Position + Action",
            ColorResourceKey = "StepMouseBrush",
            DefaultDelay = 55,
            Fields = new FieldDef[]
            {
                new("x", "Region X", FieldKind.Int, "1301"),
                new("y", "Region Y", FieldKind.Int, "0"),
                new("w", "Region width", FieldKind.Int, "378"),
                new("h", "Region height", FieldKind.Int, "1049"),
                new("action", "Action after arrival", FieldKind.Combo, "moveOnly", new[] { "moveOnly", "leftClick", "rightClick", "scroll" }),
                new("scrollDelta", "Scroll delta (negative = down)", FieldKind.Int, "-1", HideWhenKey: "action", HideUnlessValue: "scroll"),
                new("pauseBeforeMin", "Reaction pause BEFORE move — min (ms)", FieldKind.Int, "120"),
                new("pauseBeforeMax", "Reaction pause BEFORE move — max (ms)", FieldKind.Int, "450"),
                new("pauseAfterMin", "Settle pause AFTER arrival — min (ms)", FieldKind.Int, "150"),
                new("pauseAfterMax", "Settle pause AFTER arrival — max (ms)", FieldKind.Int, "600"),
                new("midPauseChance", "Mid-path hesitation chance %", FieldKind.Int, "12"),
                new("midPauseMin", "Hesitation pause — min (ms)", FieldKind.Int, "100"),
                new("midPauseMax", "Hesitation pause — max (ms)", FieldKind.Int, "400"),
                new("overshootChance", "Overshoot & correct chance %", FieldKind.Int, "15"),
                new("curveMinPct", "Path curvature MIN %", FieldKind.Int, "15"),
                new("curveMaxPct", "Path curvature MAX %", FieldKind.Int, "45"),
                new("moveTimeMin", "Movement duration — min (ms)", FieldKind.Int, "0"),
                new("moveTimeMax", "Movement duration — max (ms)", FieldKind.Int, "0"),
            },
            Summarize = s => Summarize(s),
            Commands = s => BuildCommands(s),
        };
    }

    public static string Summarize(StepNode s)
    {
        var action = PropEx.GetString(s.Props, "action", "moveOnly");
        var verb = action switch
        {
            "leftClick" => "left click",
            "rightClick" => "right click",
            "scroll" => $"scroll {PropEx.GetInt(s.Props, "scrollDelta", -1)}",
            _ => "move only",
        };
        return $"Random Mouse Position + {verb} in region [{PropEx.GetInt(s.Props, "x")},{PropEx.GetInt(s.Props, "y")} {PropEx.GetInt(s.Props, "w", 100)}x{PropEx.GetInt(s.Props, "h", 100)}]";
    }

    /// <summary>Selects one destination inside the region exactly once and plans
    /// from the real cursor position supplied by the caller.</summary>
    public static Selection Select(Point realCursor, Region region, HumanMouse.Config config,
                                   HumanMouse.PausePlanner pauses, Random rng,
                                   int screenWidth, int screenHeight)
    {
        var r = region.Normalize();
        var destination = new Point(r.X + rng.Next(r.Width), r.Y + rng.Next(r.Height));
        var plan = HumanMouse.PlanMove(realCursor.X, realCursor.Y, destination.X, destination.Y,
                                       config, pauses, rng, screenWidth, screenHeight);
        return new Selection(realCursor, destination, plan);
    }

    /// <summary>Builds app-side commands for the generic RunEngine default path.
    /// The final waypoint is emitted before the action; no action can precede arrival.
    /// DLY commands keep pauses on the PC and are never sent to the board.</summary>
    public static IReadOnlyList<string> BuildCommands(StepNode s)
    {
        var rng = new Random();
        var cfg = HumanMouse.Config.FromProps(s.Props, 0, 2300);
        var planner = new HumanMouse.PausePlanner(rng);
        var start = System.Windows.Forms.Cursor.Position;
        var selection = Select(start,
            new Region(PropEx.GetInt(s.Props, "x"), PropEx.GetInt(s.Props, "y"),
                       PropEx.GetInt(s.Props, "w", 100), PropEx.GetInt(s.Props, "h", 100)),
            cfg, planner, rng, SystemInformation.VirtualScreen.Width, SystemInformation.VirtualScreen.Height);

        var commands = new List<string>();
        if (selection.Plan.BeforeMs > 0) commands.Add($"DLY|{selection.Plan.BeforeMs}");
        foreach (var point in selection.Plan.Waypoints)
        {
            commands.Add($"MMOVE|{point.X},{point.Y},abs,0");
            if (point.DelayMs > 0) commands.Add($"DLY|{point.DelayMs}");
        }
        if (selection.Plan.AfterMs > 0) commands.Add($"DLY|{selection.Plan.AfterMs}");
        if (selection.Plan.LongPauseMs > 0) commands.Add($"DLY|{selection.Plan.LongPauseMs}");

        var action = PropEx.GetString(s.Props, "action", "moveOnly");
        if (action == "leftClick") commands.Add("MCLICK|left,1");
        else if (action == "rightClick") commands.Add("MCLICK|right,1");
        else if (action == "scroll") commands.Add($"MWHEEL|{PropEx.GetInt(s.Props, "scrollDelta", -1)}");
        return commands;
    }

    public static string ActionCommand(ActionKind action, int scrollDelta = -1)
        => action switch
        {
            ActionKind.LeftClick => "MCLICK|left,1",
            ActionKind.RightClick => "MCLICK|right,1",
            ActionKind.Scroll => $"MWHEEL|{scrollDelta}",
            _ => "",
        };

    /// <summary>Executes a preplanned selection for callers that already own a
    /// bridge. The final waypoint is checked before the action is sent.</summary>
    public static async Task<Point> ExecuteAsync(IBoardBridge bridge, Selection selection,
                                                  ActionKind action, int scrollDelta = -1,
                                                  CancellationToken ct = default)
    {
        if (selection.Plan.Waypoints.Count == 0)
            throw new InvalidOperationException("Human mouse planner returned no waypoints.");
        var points = selection.Plan.Waypoints.Select(w => (w.X, w.Y, w.DelayMs)).ToList();
        await bridge.SendPathAsync(points, ct);
        var last = selection.Plan.Waypoints[^1];
        if (last.X != selection.Destination.X || last.Y != selection.Destination.Y)
            throw new InvalidOperationException("Human mouse plan did not end at its destination.");
        var command = ActionCommand(action, scrollDelta);
        if (command.Length > 0) await bridge.SendAsync(command, null, ct);
        return selection.Destination;
    }
}
