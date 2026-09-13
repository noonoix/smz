from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")


path = "ams-shell/src/Ams.UI/Services/AutoCycleFirmwareBundle.cs"
replace_once(
    path,
    '        code=NormalizeBuzzerForManifest(code);\n        var manifest=',
    '        code=NormalizeBuzzerForManifest(code);\n        code=NormalizeMouseReliabilityForManifest(code);\n        var manifest=')
replace_once(
    path,
    '        code=PreserveKtextWhitespace(code);\n        foreach(var marker',
    '        code=PreserveKtextWhitespace(code);\n        code=ApplyMouseReliabilityAfterManifest(code);\n        foreach(var marker')

methods = r'''    // The AutoCycle manifest intentionally targets the accepted 0.9.64f baseline.
    // Normal export now hardens MCLICK/HOSTUSB first, so temporarily normalize only those
    // fragments, apply the manifest, then reapply the reliability contract to its output.
    private static string NormalizeMouseReliabilityForManifest(string code)
    {
        code=code.Replace("FAST_MOUSE_PREFIXES = (\"MMOVE\", \"MWHEEL\", \"MDOWN\", \"MUP\")",
                          "MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\", \"MWHEEL\", \"MDOWN\", \"MUP\")",StringComparison.Ordinal);
        code=code.Replace("_last_hostusb_event = [None]  # forward identical HOSTUSB heartbeats once\n","",StringComparison.Ordinal);
        const string reliableEvent="        if line.startswith(\"EVT|\"):\n            if line.startswith(\"EVT|HOSTUSB|\"):\n                if line == _last_hostusb_event[0]:\n                    continue\n                _last_hostusb_event[0] = line\n            _serial_write_line(line)              # changed events reach the PC once\n            continue";
        const string legacyEvent="        if line.startswith(\"EVT|\"):\n            _serial_write_line(line)              # arm events reach the PC live\n            continue";
        code=RequireReplace(code,reliableEvent,legacyEvent,"normal HOSTUSB baseline");
        var helperStart=code.IndexOf("def _mclick_timeout(line):",StringComparison.Ordinal);
        var sampleStart=helperStart>=0?code.IndexOf("def sample():",helperStart,StringComparison.Ordinal):-1;
        if(helperStart<0||sampleStart<0)throw new InvalidDataException("MCLICK timeout helper baseline پیدا نشد.");
        code=code.Remove(helperStart,sampleStart-helperStart);
        const string reliableDispatch="    if head == \"MCLICK\":\n        return forward_to_arm(line, _mclick_timeout(line))\n    if head in FAST_MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        const string legacyDispatch="    if head in MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        code=RequireReplace(code,reliableDispatch,legacyDispatch,"normal MCLICK dispatch");
        code=RequireReplace(code,
            "                return self._ok(forward_to_arm(line, _mclick_timeout(line)), \"MCLICK\")\n\n            def ktext",
            "                forward_fast(line)\n\n            def ktext","normal plan MCLICK dispatch");
        return code;
    }
    private static string ApplyMouseReliabilityAfterManifest(string code)
    {
        code=RequireReplace(code,
            "MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\", \"MWHEEL\", \"MDOWN\", \"MUP\")",
            "FAST_MOUSE_PREFIXES = (\"MMOVE\", \"MWHEEL\", \"MDOWN\", \"MUP\")","cycle mouse prefixes");
        code=RequireReplace(code,"parts[1] in MOUSE_PREFIXES","parts[1] in FAST_MOUSE_PREFIXES","cycle mouse ACK filter");
        const string helper="def _mclick_timeout(line):\n    \"\"\"Physical-completion timeout for all randomized holds and inter-click gaps.\"\"\"\n    try:\n        fields = line.split(\"|\", 1)[1].split(\",\")\n        count = max(1, int(fields[1])) if len(fields) > 1 else 1\n        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45\n        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin\n        return max(5.0, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)\n    except Exception:\n        return 5.0\n\n\n";
        code=RequireReplace(code,"def sample():",helper+"def sample():","cycle MCLICK timeout helper");
        const string legacyDispatch="    if head in MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        const string reliableDispatch="    if head == \"MCLICK\":\n        return forward_to_arm(line, _mclick_timeout(line))\n    if head in FAST_MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        code=RequireReplace(code,legacyDispatch,reliableDispatch,"cycle MCLICK dispatch");
        code=RequireReplace(code,
            "                forward_fast(line)\n\n            def ktext",
            "                return self._ok(forward_to_arm(line, _mclick_timeout(line)), \"MCLICK\")\n\n            def ktext","cycle plan MCLICK dispatch");
        return code;
    }
    private static string RequireReplace(string text,string oldText,string newText,string label)
    {
        if(text.CountOccurrences(oldText)!=1)throw new InvalidDataException("قرارداد "+label+" یکتا نیست.");
        return text.Replace(oldText,newText,StringComparison.Ordinal);
    }
'''
replace_once(
    path,
    '    // A KTEXT payload may intentionally end with a literal space:',
    methods + '    // A KTEXT payload may intentionally end with a literal space:')

Path("tests/AutoCycleMouseReliabilityTests.cs").write_text(r'''using System;
using System.IO;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class AutoCycleMouseReliabilityTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var baseline = PicoFirmwareExporter.BuildCodePy(Array.Empty<PicoFirmwareExporter.LightState>(), "cycle-mouse-test");
        var manifest = Path.Combine(AppContext.BaseDirectory, "portable-runtime", "autocycle_h6_patch.json");
        var cycle = AutoCycleFirmwareBundle.PatchCode(baseline, manifest);
        if (!cycle.Contains("if head == \"MCLICK\":", StringComparison.Ordinal)
            || !cycle.Contains("forward_to_arm(line, _mclick_timeout(line))", StringComparison.Ordinal))
            throw new Exception("AutoCycle lost serialized MCLICK completion");
        if (!cycle.Contains("changed = (not _arm_host_usb_seen or state != _arm_host_usb_state)", StringComparison.Ordinal))
            throw new Exception("AutoCycle lost HOSTUSB state deduplication");
    }
}
''', encoding="utf-8")
print("AutoCycle mouse reliability baseline synchronized")
