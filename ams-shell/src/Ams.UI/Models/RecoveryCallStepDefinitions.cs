using System.Reflection;
using System.Runtime.CompilerServices;

namespace Ams.UI.Models;

/// <summary>Registers explicit recovery-call actions and the atomic Key Hold group.</summary>
internal static class RecoveryCallStepDefinitions
{
    public const string CallMain = "callMainDcRecovery";
    public const string CallLaunch = "callLaunchDcRecovery";
    public const string KeyHold = "keyHold";

    [ModuleInitializer]
    internal static void Register()
    {
        var field = typeof(StepDefinitions).GetField("Defs", BindingFlags.Static | BindingFlags.NonPublic);
        if (field?.GetValue(null) is not Dictionary<string, StepDefinition> definitions)
            throw new InvalidOperationException("Step definition registry is unavailable.");

        definitions[KeyHold] = new StepDefinition
        {
            Label = "Key Hold Group",
            ColorResourceKey = "StepKeyboardBrush",
            DefaultDelay = 0,
            IsContainer = true,
            IsScopeContainer = true,
            Fields = new[]
            {
                new FieldDef("key", "Held key", FieldKind.Combo, "SHIFT", KeyMap.KeyNames.ToArray()),
            },
            Summarize = s => $"Key Hold {PropEx.GetString(s.Props, "key", "SHIFT")} · {s.Children.Count} action(s) while held",
            // RunEngine owns the key-down/children/key-up transaction.
        };

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
