from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def edit(rel, fn):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    updated = fn(text)
    if updated == text:
        raise SystemExit(f'no change made to {rel}')
    path.write_text(updated, encoding='utf-8')

# Step registry: per-step timeout choice for sound/light and a first-class fatal step.
def step_defs(s):
    marker = '        ["forLoop"] = new StepDefinition'
    error = '''        ["raiseError"] = new StepDefinition
        {
            Label = "Raise Error / Stop Macro", ColorResourceKey = "StepErrorBrush", DefaultDelay = 0,
            Fields = new FieldDef[]
            {
                new("message", "Error message", FieldKind.Multiline, "A deliberate error stopped the macro."),
            },
            Summarize = s =>
            {
                var m = PropEx.GetString(s.Props, "message", "A deliberate error stopped the macro.").Replace('\\n', ' ').Trim();
                if (m.Length > 56) m = m[..56] + "…";
                return "⛔ Raise Error · " + m;
            },
            // PC-side safety step: RunEngine records it, starts the buzzer alarm, and stops immediately.
        },
'''
    if marker not in s or 'raiseError' in s:
        raise SystemExit('StepDefinitions insertion marker missing or already applied')
    s = s.replace(marker, error + marker, 1)
    sound_old = '                new("timeoutMs", "Timeout (ms) — legacy system used 20000 (§17.2)", FieldKind.Int, "20000"),\n'
    sound_new = sound_old + '                new("onTimeout", "On timeout", FieldKind.Combo, "global", new[] { "global", "stopWithAlarm", "stopQuiet", "continue" }),\n'
    if sound_old not in s:
        raise SystemExit('sound timeout field missing')
    s = s.replace(sound_old, sound_new, 1)
    light_old = '                new("timeoutMs", "Timeout (ms)", FieldKind.Int, "20000"),\n'
    light_new = light_old + '                new("onTimeout", "On timeout", FieldKind.Combo, "global", new[] { "global", "stopWithAlarm", "stopQuiet", "continue" }),\n'
    if light_old not in s:
        raise SystemExit('light timeout field missing')
    s = s.replace(light_old, light_new, 1)
    # Summaries make the selected behavior visible in the step list, not only inside the dialog.
    anchor = '    private static string StableSecText(StepNode s)\n        => PropEx.GetDouble(s.Props, "stableSec", 2).ToString("0.#", CultureInfo.InvariantCulture);\n'
    helper = anchor + '''\n    private static string TimeoutPolicyText(StepNode s)\n        => PropEx.GetString(s.Props, "onTimeout", "global") switch\n        {\n            "stopWithAlarm" => "timeout → alarm + stop",\n            "stopQuiet" => "timeout → quiet stop",\n            "continue" => "timeout → continue",\n            _ => "timeout → global policy",\n        };\n'''
    if anchor not in s:
        raise SystemExit('StableSecText anchor missing')
    s = s.replace(anchor, helper, 1)
    s = s.replace('$"If Sound ≥{PropEx.GetInt(s.Props, "threshold", 90)} · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms"', '$"If Sound ≥{PropEx.GetInt(s.Props, "threshold", 90)} · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms · {TimeoutPolicyText(s)}"', 1)
    s = s.replace('$"Wait for sound ≥{PropEx.GetInt(s.Props, "threshold", 90)} · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms"', '$"Wait for sound ≥{PropEx.GetInt(s.Props, "threshold", 90)} · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms · {TimeoutPolicyText(s)}"', 1)
    s = s.replace('$"If Light {LuxLow(s)}-{LuxHigh(s)} lux for {StableSecText(s)}s · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms"', '$"If Light {LuxLow(s)}-{LuxHigh(s)} lux for {StableSecText(s)}s · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms · {TimeoutPolicyText(s)}"', 1)
    s = s.replace('$"Wait for light {LuxLow(s)}-{LuxHigh(s)} lux for {StableSecText(s)}s · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms"', '$"Wait for light {LuxLow(s)}-{LuxHigh(s)} lux for {StableSecText(s)}s · timeout {PropEx.GetInt(s.Props, "timeoutMs", 20000)}ms · {TimeoutPolicyText(s)}"', 1)
    return s
edit('ams-shell/src/Ams.UI/Models/StepDefinitions.cs', step_defs)

# Persian label for the new error-step field.
def step_texts(s):
    marker = '        // ── misc ──\n'
    ins = '        ["message"] = "پیام خطا (با رسیدن به این استپ، ماکرو فوراً متوقف و با بازر هشدار داده می‌شود)",\n\n'
    if marker not in s or 'پیام خطا (با رسیدن' in s:
        raise SystemExit('StepTextsFa marker missing or already applied')
    return s.replace(marker, marker + ins, 1)
edit('ams-shell/src/Ams.UI/Models/StepTextsFa.cs', step_texts)

# Force the explicit error step to use the Pico buzzer when configured, while preserving PC fallback.
error_alarm = '''namespace Ams.UI.Services;

/// <summary>Cancellable PC/Pico fallback alarm. The portable runtime owns Pico-side alarms;
/// the desktop runner can provide a Pico beep callback for an active board connection.</summary>
public sealed class ErrorAlarm : IDisposable
{
    private readonly CancellationTokenSource _cts = new();
    private readonly Task _loop;
    private readonly Func<Task>? _picoBeep;

    private ErrorAlarm(ErrorPolicySettings policy, Func<Task>? picoBeep)
    {
        _picoBeep = picoBeep;
        _loop = Task.Run(async () =>
        {
            var until = policy.AlarmDurationSeconds > 0 ? DateTimeOffset.UtcNow.AddSeconds(policy.AlarmDurationSeconds) : DateTimeOffset.MaxValue;
            do
            {
                if (policy.AlarmSource is "pc" or "both")
                {
                    try { Console.Beep(880, 180); } catch { }
                }
                if (policy.AlarmSource is "pico" or "both" && _picoBeep is not null)
                {
                    try { await _picoBeep(); } catch { }
                }
                if (!policy.RepeatAlarm) break;
                await Task.Delay(850, _cts.Token);
            } while (DateTimeOffset.UtcNow < until && !_cts.IsCancellationRequested);
        }, _cts.Token);
    }

    public static ErrorAlarm? Start(ErrorPolicySettings policy, Func<Task>? picoBeep = null, bool force = false)
    {
        if (!force && !policy.FatalAlarmEnabled) return null;
        bool pc = policy.AlarmSource is "pc" or "both";
        bool pico = policy.AlarmSource is "pico" or "both" && picoBeep is not null;
        return pc || pico ? new ErrorAlarm(policy, picoBeep) : null;
    }

    public void Dispose()
    {
        if (_cts.IsCancellationRequested) return;
        _cts.Cancel();
        try { _loop.Wait(250); } catch { }
        _cts.Dispose();
    }
}
'''
(ROOT / 'ams-shell/src/Ams.UI/Services/ErrorAlarm.cs').write_text(error_alarm, encoding='utf-8')

def bootstrap(s):
    old = '    public static bool Handle(Exception error, string source, string? tab = null)\n'
    new = '    public static bool Handle(Exception error, string source, string? tab = null, Func<Task>? picoBeep = null, bool forceAlarm = false)\n'
    if old not in s:
        raise SystemExit('ErrorPolicyBootstrap signature missing')
    s = s.replace(old, new, 1)
    old2 = '            if (!Settings.FatalAlarmEnabled) return false;\n            _alarm?.Dispose();\n            _alarm = ErrorAlarm.Start(Settings);\n'
    new2 = '            if (!Settings.FatalAlarmEnabled && !forceAlarm) return false;\n            _alarm?.Dispose();\n            _alarm = ErrorAlarm.Start(Settings, picoBeep, forceAlarm);\n'
    if old2 not in s:
        raise SystemExit('ErrorPolicyBootstrap alarm block missing')
    return s.replace(old2, new2, 1)
edit('ams-shell/src/Ams.UI/Services/ErrorPolicyBootstrap.cs', bootstrap)

def run_engine(s):
    marker = '                case "findImage":\n'
    case = '''                case "raiseError":
                {
                    var message = PropEx.GetString(s.Props, "message", "A deliberate error stopped the macro.").Trim();
                    if (message.Length == 0) message = "A deliberate error stopped the macro.";
                    var error = new InvalidOperationException(message);
                    ErrorPolicyBootstrap.Handle(error, "step", s.Name,\n                        () => Send("BEEP|880,180", ct, quiet: true), forceAlarm: true);
                    _log("⛔ error step: " + message + " — stopping immediately with alarm");
                    throw new PolicyStop(alarmed: true);
                }

'''
    if marker not in s or 'case "raiseError"' in s:
        raise SystemExit('RunEngine error-step marker missing or already applied')
    s = s.replace(marker, case + marker, 1)
    helper_anchor = '    private async Task<bool> RunWaitForLightAsync(StepNode s, CancellationToken ct)\n'
    helper = '''    private static string? StepTimeoutPolicy(StepNode s)
    {
        var policy = PropEx.GetString(s.Props, "onTimeout", "global");
        return policy is "stopWithAlarm" or "stopQuiet" or "continue" ? policy : null;
    }

'''
    if helper_anchor not in s:
        raise SystemExit('RunEngine wait helper anchor missing')
    s = s.replace(helper_anchor, helper + helper_anchor, 1)
    s = s.replace('var reply = await Send(cmd, ct, allowTimeout: true, timeoutSeconds: timeoutMs / 1000.0 + 10);', 'var reply = await Send(cmd, ct, allowTimeout: true, timeoutSeconds: timeoutMs / 1000.0 + 10, timeoutPolicy: StepTimeoutPolicy(s));', 2)
    sig_old = '    private async Task<string> Send(string cmd, CancellationToken ct, string? logAs = null,\n                            bool allowTimeout = false, double? timeoutSeconds = null, bool quiet = false)\n'
    sig_new = '    private async Task<string> Send(string cmd, CancellationToken ct, string? logAs = null,\n                            bool allowTimeout = false, double? timeoutSeconds = null, bool quiet = false, string? timeoutPolicy = null)\n'
    if sig_old not in s:
        raise SystemExit('RunEngine Send signature missing')
    s = s.replace(sig_old, sig_new, 1)
    policy_old = '                var policy = ErrorPolicyBootstrap.Settings.TimeoutPolicy;\n'
    policy_new = '                var policy = timeoutPolicy ?? ErrorPolicyBootstrap.Settings.TimeoutPolicy;\n'
    if policy_old not in s:
        raise SystemExit('RunEngine timeout policy line missing')
    return s.replace(policy_old, policy_new, 1)
edit('ams-shell/src/Ams.UI/Services/RunEngine.cs', run_engine)

# Visual tokens: the new step is unmistakably red in the step list and rail.
def tokens(s):
    color = '    <Color x:Key="StepErrorColor">#FFF85149</Color>\n'
    brush = '    <SolidColorBrush x:Key="StepErrorBrush" Color="{StaticResource StepErrorColor}" />\n'
    if 'StepErrorColor' in s:
        raise SystemExit('Tokens already contain StepErrorColor')
    s = s.replace('    <Color x:Key="StepAudioColor">#FFB158FF</Color>\n', '    <Color x:Key="StepAudioColor">#FFB158FF</Color>\n' + color, 1)
    return s.replace('    <SolidColorBrush x:Key="StepAudioBrush" Color="{StaticResource StepAudioColor}" />\n', '    <SolidColorBrush x:Key="StepAudioBrush" Color="{StaticResource StepAudioColor}" />\n' + brush, 1)
edit('ams-shell/src/Ams.UI/Resources/Tokens.xaml', tokens)

# Menus and rail: make the missing step discoverable everywhere.
def main_xaml(s):
    line = '<MenuItem Header="Wait For _Light (BH1750)" Command="{Binding AddStepCommand}" CommandParameter="waitForLight" />'
    add = line + '\n                <MenuItem Header="⛔ Raise Error / Stop Macro" Command="{Binding AddStepCommand}" CommandParameter="raiseError" />'
    if s.count(line) < 1:
        raise SystemExit('main menu wait-light entry missing')
    s = s.replace(line, add)
    ctx_line = '<MenuItem Header="Wait For Light (BH1750)" CommandParameter="waitForLight"\n                                      Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />'
    ctx_add = ctx_line + '\n                            <MenuItem Header="⛔ Raise Error / Stop Macro" CommandParameter="raiseError"\n                                      Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />'
    if ctx_line not in s:
        raise SystemExit('context menu wait-light entry missing')
    s = s.replace(ctx_line, ctx_add, 1)
    rail_marker = '                        <Button Style="{StaticResource RailButton}" Command="{Binding AddStepCommand}" CommandParameter="forLoop"'
    rail = '''                        <Button Style="{StaticResource RailButton}" Command="{Binding AddStepCommand}" CommandParameter="raiseError"
                                ToolTip="⛔ خطای عمدی — ثبت خطا، توقف فوری و هشدار ممتد با بازر">
                            <StackPanel>
                                <TextBlock Text="⛔" FontSize="15" FontFamily="Segoe UI Emoji" HorizontalAlignment="Center" Foreground="{StaticResource ErrorBrush}" />
                                <TextBlock Text="Error" FontSize="8" HorizontalAlignment="Center" Foreground="#FFFFFF" Margin="0,1,0,0" />
                            </StackPanel>
                        </Button>
'''
    if rail_marker not in s:
        raise SystemExit('rail insertion marker missing')
    return s.replace(rail_marker, rail + rail_marker, 1)
edit('ams-shell/src/Ams.UI/MainWindow.xaml', main_xaml)

# Minimal regression coverage for the newly exposed contracts.
def tests(s):
    marker = '        var def = StepDefinitions.Get("openFile");\n'
    add = '''        var errorDef = StepDefinitions.Get("raiseError");
        Assert(errorDef.Label == "Raise Error / Stop Macro" && errorDef.Fields.Any(f => f.Key == "message"),
            "raiseError definition exists with a message field");
        Assert(StepDefinitions.Get("waitForSound").Fields.Any(f => f.Key == "onTimeout" && f.Options!.Contains("global")),
            "waitForSound exposes a per-step timeout policy");
        Assert(StepDefinitions.Get("waitForLight").Fields.Any(f => f.Key == "onTimeout" && f.Options!.Contains("stopWithAlarm")),
            "waitForLight exposes a per-step timeout policy");

'''
    if marker not in s or 'raiseError definition exists' in s:
        raise SystemExit('TestRunner insertion marker missing or already applied')
    return s.replace(marker, add + marker, 1)
edit('tests/TestRunner.cs', tests)

print('feature patch applied')
