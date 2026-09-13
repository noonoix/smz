using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class KeyboardHeldKeyGuardTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var duplicateBridge = new KeyboardGuardBridge();
        new RunEngine(duplicateBridge, _ => { }, 1920, 1080).RunAsync(new[]
        {
            Key("keyDown", "A"),
            Key("keyDown", "A"),
            Key("keyUp", "A"),
        }, CancellationToken.None).GetAwaiter().GetResult();
        Require(duplicateBridge.Sent.Count(c => c == "KDOWN|65") == 1,
            "duplicate explicit KDOWN was not suppressed");
        Require(duplicateBridge.Sent.Count(c => c == "KUP|65") == 1,
            "paired KUP was not preserved");

        var loopBridge = new KeyboardGuardBridge();
        var loop = new StepNode
        {
            Type = "forLoop",
            Props = new Dictionary<string, object?> { ["mode"] = "count", ["count"] = 20 },
        };
        loop.Children.Add(Key("keyDown", "A"));
        loop.Children.Add(Key("keyUp", "A"));
        loop.Children.Add(Key("keystroke", "B"));
        new RunEngine(loopBridge, _ => { }, 1920, 1080)
            .RunAsync(new[] { loop }, CancellationToken.None).GetAwaiter().GetResult();
        Require(loopBridge.Sent.Count(c => c == "KDOWN|65") == 20,
            "fixture loop lost a legitimate A key down");
        Require(loopBridge.Sent.Count(c => c == "KUP|65") == 20,
            "fixture loop lost a legitimate A key up");

        var cleanupBridge = new KeyboardGuardBridge();
        new RunEngine(cleanupBridge, _ => { }, 1920, 1080)
            .RunAsync(new[] { Key("keyDown", "A") }, CancellationToken.None).GetAwaiter().GetResult();
        Require(cleanupBridge.Sent.Count(c => c == "KDOWN|65") == 1
                && cleanupBridge.Sent.Count(c => c == "KUP|65") == 1,
            "normal run completion did not release a held key");

        var errorBridge = new KeyboardGuardBridge();
        try
        {
            new RunEngine(errorBridge, _ => { }, 1920, 1080).RunAsync(new[]
            {
                Key("keyDown", "A"),
                new StepNode { Type = "raiseError", Props = new Dictionary<string, object?> { ["message"] = "fixture" } },
            }, CancellationToken.None).GetAwaiter().GetResult();
        }
        catch (RunEngine.PolicyStop) { }
        Require(errorBridge.Sent.Count(c => c == "KUP|65") == 1,
            "error exit did not release a held key");

        var routedBridge = new KeyboardGuardBridge();
        new RunEngine(routedBridge, _ => { }, 1920, 1080, picoPresent: () => true).RunAsync(new[]
        {
            Key("keyDown", "A", "promicro"),
            Key("keyDown", "A", "pico"),
        }, CancellationToken.None).GetAwaiter().GetResult();
        Require(routedBridge.Sent.Contains("KBDARM|KDOWN|65")
                && routedBridge.Sent.Contains("KBDPICO|KDOWN|65")
                && routedBridge.Sent.Contains("KBDARM|KUP|65")
                && routedBridge.Sent.Contains("KBDPICO|KUP|65"),
            "held-key state was not isolated and released per route");
    }

    private static StepNode Key(string type, string key, string? board = null)
    {
        var props = new Dictionary<string, object?> { ["key"] = key };
        if (board is not null) props["keyboardBoard"] = board;
        return new StepNode { Type = type, Props = props };
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException("Keyboard guard regression: " + message);
    }
}

internal sealed class KeyboardGuardBridge : IBoardBridge
{
    public List<string> Sent { get; } = new();
    public event EventHandler<string>? LineReceived { add { } remove { } }
    public event EventHandler<BridgeState>? StateChanged { add { } remove { } }
    public BridgeState State => BridgeState.Connected;
    public string? FirmwareVersion => "keyboard-guard-test";
    public string? Port => "FAKE";
    public Task ConnectAsync(string portName, CancellationToken ct = default) => Task.CompletedTask;
    public Task<string> SendAsync(string command, double? timeoutSeconds = null, CancellationToken ct = default)
    {
        Sent.Add(command);
        return Task.FromResult("OK|" + command.Split('|')[0]);
    }
    public Task<string> SendPathAsync(IReadOnlyList<(int X, int Y, int DelayMs)> points, CancellationToken ct = default)
        => Task.FromResult("OK|PATH");
    public Task SendAbortAsync() => Task.CompletedTask;
    public Task DisconnectAsync(CancellationToken ct = default) => Task.CompletedTask;
    public ValueTask DisposeAsync() => ValueTask.CompletedTask;
}
