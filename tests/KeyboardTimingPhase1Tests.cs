using System;
using System.IO;
using System.Runtime.CompilerServices;

namespace Ams.Tests;

internal static class KeyboardTimingPhase1Tests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var root = FindRepositoryRoot();
        var project = File.ReadAllText(Path.Combine(root, "ams-shell", "src", "Ams.UI", "Ams.UI.csproj"));
        var wrapper = File.ReadAllText(Path.Combine(root, "ams-shell", "bridge", "bridge_fast_keyboard.py"));

        Assert(project.Contains("<Link>bridge\\bridge_core.py</Link>"),
            "the proven bridge is not packaged as bridge_core.py");
        Assert(project.Contains("<Link>bridge\\bridge.py</Link>"),
            "the low-latency bridge launcher is not packaged as bridge.py");
        Assert(wrapper.Contains("PICO_COMMAND_READ_TIMEOUT_S = 0.01"),
            "Pico keyboard command reads are not configured for 10 ms latency");
        Assert(wrapper.Contains("_original_pico_connect(self)"),
            "the wrapper no longer preserves the proven connect/ACK contract");
        Assert(!wrapper.Contains("self._send(cmd)"),
            "keyboard commands must not become fire-and-forget; ACK/error semantics must remain intact");
    }

    private static string FindRepositoryRoot()
    {
        DirectoryInfo? d = new(AppContext.BaseDirectory);
        for (int i = 0; i < 10 && d is not null; i++, d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "ams-shell", "bridge", "bridge.py")))
                return d.FullName;
        throw new Exception("repository root not found for keyboard timing contract tests");
    }

    private static void Assert(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }
}
