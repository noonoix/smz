using System.Runtime.CompilerServices;
using Ams.UI.Models;

internal static class RecoveryEntryPolicyContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var passed = 0;
        var failed = 0;
        void Check(bool condition, string name)
        {
            if (condition) { passed++; Console.WriteLine("PASS: " + name); }
            else { failed++; Console.WriteLine("FAIL: " + name); }
        }

        Check(RecoveryEntryPolicy.PreludeKeys(RecoveryEntryReason.Login).Count == 0,
            "normal login enters the shared recovery flow without a prelude key");
        Check(RecoveryEntryPolicy.PreludeKeys(RecoveryEntryReason.Disconnect)
                .SequenceEqual(new[] { "ESC" }),
            "disconnect prepends exactly one ESC before the shared login flow");
        Check(RecoveryEntryPolicy.PreludeKeys(RecoveryEntryReason.Disconnect).Count == 1,
            "disconnect policy cannot duplicate the shared login macro");

        Console.WriteLine($"=== Recovery entry policy results: {passed} passed, {failed} failed ===");
        if (failed > 0) throw new InvalidOperationException($"Recovery entry policy contract failed: {failed}");
    }
}
