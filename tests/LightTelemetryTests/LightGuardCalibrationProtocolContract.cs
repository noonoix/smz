using System.Runtime.CompilerServices;
using Ams.UI.Services;

internal static class LightGuardCalibrationProtocolContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var checks = new List<(bool Passed, string Name)>();
        void Check(bool condition, string name) => checks.Add((condition, name));

        Check(LightGuardCalibrationProtocol.ProfileIds.Count == 6,
            "Guard has exactly six optical profiles");
        Check(LightGuardCalibrationProtocol.ProfileIds.Contains("login-or-dc")
              && !LightGuardCalibrationProtocol.ProfileIds.Contains("login"),
            "Login and DC share one optical calibration profile");

        var stable = LightGuardCalibrationProtocol.Compute(
            "desktop", new[] { 10.0, 10.5, 9.8, 10.2, 10.1 }, 750, 5.0);
        Check(stable is not null
              && stable.Center == 10.1
              && Math.Abs(stable.Spread - 0.7) < 0.000001
              && stable.Tolerance == 2.0,
            "five-second estimator produces median, spread and minimum tolerance");

        var unstable = LightGuardCalibrationProtocol.Compute(
            "game", new[] { 1.0, 2.0, 3.0, 8.0, 9.0 }, 750, 5.0);
        Check(unstable is null, "unstable spread is rejected");

        var command = LightGuardCalibrationProtocol.BuildCalSet("rev-1", stable!);
        Check(command == "CALSET|rev-1|desktop|10.1|2|750",
            "CALSET is deterministic and invariant-culture formatted");

        var identity = LightGuardCalibrationProtocol.TryParseIdentity(
            "OK|PONG|pico-light-guard 1.0.0|role=light-guard|hid=off|uart=off|actuator=off|sensor=BH1750|button=GP4,GP3|buzzer=GP6|profiles=6",
            out var parsedIdentity);
        Check(identity && parsedIdentity is not null && parsedIdentity.ProfileCount == 6
              && parsedIdentity.HidOff && parsedIdentity.UartOff && parsedIdentity.ActuatorOff,
            "Guard PING identity requires HID, UART and actuator off");

        var state = LightGuardCalibrationProtocol.TryParseStateEvent(
            "EVT|GUARD|state=game|lux=26.5|revision=rev-1", out var parsedState);
        Check(state && parsedState is not null && parsedState.ProfileId == "game"
              && parsedState.Lux == 26.5 && parsedState.Revision == "rev-1",
            "Guard state events parse only allowlisted profiles");

        var injectionRejected = false;
        try { LightGuardCalibrationProtocol.BuildCalSet("bad|revision", stable!); }
        catch (ArgumentException) { injectionRejected = true; }
        Check(injectionRejected, "CALSET rejects delimiter injection");

        foreach (var check in checks)
            Console.WriteLine((check.Passed ? "PASS: " : "FAIL: ") + check.Name);
        var failed = checks.Count(x => !x.Passed);
        Console.WriteLine($"=== Light Guard protocol results: {checks.Count - failed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Light Guard protocol contract failed: {failed}");
    }
}
