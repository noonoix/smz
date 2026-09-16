using Ams.UI.Models;
using Ams.UI.Services;
using System.Runtime.CompilerServices;

internal static class LightGuardAppAdapterContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = new List<(bool Passed, string Name)>();
        void Check(bool value, string name) => checks.Add((value, name));

        var profiles = LightStateDefaults.CreateInitialProfiles();
        var revision = LightGuardAppAdapter.ComputeRevision(profiles);
        Check(revision.StartsWith("guard-", StringComparison.Ordinal) && revision.Length == 22,
            "Guard revision is deterministic and token-safe");
        Check(revision == LightGuardAppAdapter.ComputeRevision(profiles),
            "same six profiles produce the same revision");

        var calset = LightGuardAppAdapter.BuildCalSet(revision, profiles[0]);
        Check(calset.StartsWith("CALSET|guard-", StringComparison.Ordinal)
              && calset.Contains("|desktop|", StringComparison.Ordinal),
            "app adapter builds a CALSET for the canonical desktop profile");

        Check(LightGuardAppAdapter.TryParseCalGet(
            "OK|CALGET|revision=" + revision + "|count=6", out var calget)
              && calget is not null && calget.Count == 6 && calget.Revision == revision,
            "CALGET parses revision and complete profile count");

        Check(LightGuardAppAdapter.TryExtractEventLine(
            "{\"event\":\"evt\",\"line\":\"EVT|CAL|mode=ready|stage=1|id=desktop|seconds=5\"}",
            out var eventLine)
              && eventLine.StartsWith("EVT|CAL|", StringComparison.Ordinal),
            "bridge JSON unwraps Guard calibration events");
        Check(LightGuardAppAdapter.TryParseCalibrationEvent(eventLine, out var calibration)
              && calibration is not null && calibration.Mode == "ready"
              && calibration.Stage == 1 && calibration.ProfileId == "desktop",
            "physical calibration stage events parse safely");

        Check(LightGuardAppAdapter.TryParseCalibrationEvent(
            "EVT|CAL|mode=saved-stage|stage=3|id=character-dashboard|saved=1", out var saved)
              && saved is not null && saved.Mode == "saved-stage"
              && saved.Stage == 3 && saved.ProfileId == "character-dashboard",
            "yellow save event identifies the targeted dashboard position");
        Check(LightGuardAppAdapter.TryParseCalibrationEvent(
            "EVT|CAL|mode=exited|saved=1", out var exited)
              && exited is not null && exited.Mode == "exited",
            "blue long-hold exit event parses partial calibration completion");

        var changed = LightStateDefaults.CreateInitialProfiles();
        changed[0].LuxCenter = 1;
        Check(revision != LightGuardAppAdapter.ComputeRevision(changed),
            "changing one profile invalidates the synchronization revision");

        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Light Guard app adapter results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Light Guard app adapter contract failed: {failed}");
    }
}
