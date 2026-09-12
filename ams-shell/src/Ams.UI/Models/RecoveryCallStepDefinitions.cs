using System.Reflection;
using System.Runtime.CompilerServices;

namespace Ams.UI.Models;

/// <summary>
/// Registers explicit recovery-call actions without coupling light detection to recovery.
/// The user places these leaf steps inside any existing If branch.
/// </summary>
internal static class RecoveryCallStepDefinitions
{
    public const string CallMain = "callMainDcRecovery";
    public const string CallLaunch = "callLaunchDcRecovery";

    [ModuleInitializer]
    internal static void Register()
    {
        var field = typeof(StepDefinitions).GetField("Defs", BindingFlags.Static | BindingFlags.NonPublic);
        if (field?.GetValue(null) is not Dictionary<string, StepDefinition> definitions)
            throw new InvalidOperationException("Step definition registry is unavailable.");

        definitions[CallMain] = new StepDefinition
        {
            Label = "Run/Call Main DC Recovery",
            ColorResourceKey = "StepFlowBrush",
            DefaultDelay = 0,
            Fields = Array.Empty<FieldDef>(),
            Summarize = _ => "↪ Run/Call Main DC Recovery",
        };
        definitions[CallLaunch] = new StepDefinition
        {
            Label = "Run/Call Launch DC Recovery",
            ColorResourceKey = "StepFlowBrush",
            DefaultDelay = 0,
            Fields = Array.Empty<FieldDef>(),
            Summarize = _ => "↪ Run/Call Launch DC Recovery",
        };
    }
}
