from pathlib import Path


def once(path, old, new):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if s.count(old)!=1: raise SystemExit(f'{path}: expected one match, got {s.count(old)}')
    p.write_text(s.replace(old,new),encoding='utf-8')

# UI: same three insertion surfaces, new portable buzzer action.
p=Path('ams-shell/src/Ams.UI/MainWindow.xaml'); s=p.read_text(encoding='utf-8')
count=s.count('CommandParameter="playAudio"')
if count != 3: raise SystemExit(f'expected 3 playAudio insertion surfaces, got {count}')
s=s.replace('CommandParameter="playAudio"','CommandParameter="buzzer"')
s=s.replace('Header="Play Audio"','Header="Buzzer Beep"')
p.write_text(s,encoding='utf-8')

# New definition; legacy playAudio remains registered for old .amsj files.
p=Path('ams-shell/src/Ams.UI/Models/StepDefinitions.cs'); s=p.read_text(encoding='utf-8')
marker='        ["playAudio"] = new StepDefinition\n'
if s.count(marker)!=1: raise SystemExit('playAudio definition marker not found')
block='''        ["buzzer"] = new StepDefinition
        {
            Label = "Buzzer Beep", ColorResourceKey = "StepFlowBrush", DefaultDelay = 0,
            Fields = new FieldDef[]
            {
                new("preset", "Tone pattern", FieldKind.Combo, "short", new[] { "short", "double", "warning", "success", "custom" }),
                new("pattern", "Custom sequence — freq:duration,pause;... (example 900:150,80;1200:250)", FieldKind.Text,
                    "900:150,80;1200:250", HideWhenKey: "preset", HideUnlessValue: "custom"),
            },
            Summarize = s => "Buzzer · " + (PropEx.GetString(s.Props, "preset", "short") == "custom"
                ? PropEx.GetString(s.Props, "pattern", "900:150")
                : PropEx.GetString(s.Props, "preset", "short")),
            Commands = s => BuildBuzzerCommands(s.Props),
        },
'''
s=s.replace(marker,block+marker)
# Add parser before public Get.
marker2='    public static StepDefinition Get(string type)\n'
if s.count(marker2)!=1: raise SystemExit('Get marker not found')
helper='''    /// <summary>Builds the GP6 passive-buzzer contract. Custom syntax is
    /// freq:duration,pause;freq:duration (Hz/ms); pause is optional after each tone.</summary>
    public static IReadOnlyList<string> BuildBuzzerCommands(IReadOnlyDictionary<string, object?> p)
    {
        string preset = PropEx.GetString(p, "preset", "short");
        string pattern = preset switch
        {
            "short" => "1000:180",
            "double" => "1000:140,100;1000:140",
            "warning" => "700:180,90;700:180,90;700:300",
            "success" => "900:120,70;1300:220",
            "custom" => PropEx.GetString(p, "pattern", "900:150"),
            _ => throw new FormatException("unknown buzzer preset '" + preset + "'"),
        };
        var commands = new List<string>();
        foreach (var raw in pattern.Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var sides = raw.Split(':', 2, StringSplitOptions.TrimEntries);
            var timing = sides.Length == 2 ? sides[1].Split(',', StringSplitOptions.TrimEntries) : Array.Empty<string>();
            if (sides.Length != 2 || timing.Length is < 1 or > 2
                || !int.TryParse(sides[0], out int freq) || !int.TryParse(timing[0], out int duration)
                || (timing.Length == 2 && !int.TryParse(timing[1], out _)))
                throw new FormatException("buzzer pattern must be freq:duration,pause;... (Hz/ms)");
            int pause = timing.Length == 2 ? int.Parse(timing[1]) : 0;
            if (freq is < 30 or > 20000) throw new FormatException("buzzer frequency must be 30..20000 Hz");
            if (duration <= 0 || pause < 0) throw new FormatException("buzzer duration must be positive and pause non-negative");
            commands.Add($"BEEP|{freq},{duration}");
            if (pause > 0) commands.Add($"DLY|{pause}");
        }
        if (commands.Count == 0) throw new FormatException("buzzer pattern is empty");
        return commands;
    }

'''
s=s.replace(marker2,helper+marker2)
p.write_text(s,encoding='utf-8')

# Persian labels.
p=Path('ams-shell/src/Ams.UI/Models/StepTextsFa.cs'); s=p.read_text(encoding='utf-8')
needle='        ["playAudio:path"] = "فایل صوتی (wav / mp3)",\n'
if s.count(needle)!=1: raise SystemExit('StepTextsFa playAudio marker not found')
s=s.replace(needle,'        ["buzzer:preset"] = "نوع صدای بوق (short / double / warning / success / custom)",\n        ["buzzer:pattern"] = "الگوی سفارشی — فرکانس:مدت,مکث;... نمونه: 900:150,80;1200:250",\n'+needle)
p.write_text(s,encoding='utf-8')

# Portable plan exporter: compile buzzer directly; legacy playAudio stays PC-compatible.
p=Path('ams-shell/src/Ams.UI/Services/PlanExporter.cs'); s=p.read_text(encoding='utf-8')
old='case "runExe":EmitLaunch(n,false);return; case "openFile":EmitLaunch(n,true);return; case "playAudio":EmitAudio(n);return; case "playScript":EmitInclude(n);return;'
new='case "runExe":EmitLaunch(n,false);return; case "openFile":EmitLaunch(n,true);return; case "playAudio":EmitAudio(n);return; case "buzzer":EmitBuzzer(n);return; case "playScript":EmitInclude(n);return;'
if s.count(old)!=1: raise SystemExit('PlanExporter switch marker not found')
s=s.replace(old,new)
marker='        private void EmitAudio(StepNode n)'
if s.count(marker)!=1: raise SystemExit('EmitAudio marker not found')
method='''        private void EmitBuzzer(StepNode n)
        {
            try
            {
                var ops = StepDefinitions.BuildBuzzerCommands(n.Props)
                    .Select(c => c.StartsWith("DLY|", StringComparison.Ordinal) ? "DELAY|" + c[4..] : c);
                Emit(n, ops, "BEEP");
            }
            catch (FormatException ex) { Error(n, ex.Message); }
        }

'''
s=s.replace(marker,method+marker)
s=s.replace('pwmio.PWMOut(board.GP5, duty_cycle=0,','pwmio.PWMOut(board.GP6, duty_cycle=0,')
p.write_text(s,encoding='utf-8')

# Exported Pico firmware: host BEEP support and correct physical pin.
for fn in ['ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs','portable/plan3/CIRCUITPY/code.py','portable/plan3/CIRCUITPY-SPLIT/code.py']:
    p=Path(fn)
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8')
    s=s.replace('pwmio.PWMOut(board.GP5, duty_cycle=0,','pwmio.PWMOut(board.GP6, duty_cycle=0,')
    marker='            if line in ("HALT", "BYE"):' if fn.endswith('.cs') else '    if line in ("HALT", "BYE"):'
    if marker not in s: raise SystemExit(f'{fn}: HALT marker not found')
    indent='            ' if fn.endswith('.cs') else '    '
    host='''if line.startswith("BEEP|"):
                try:
                    import pwmio
                    a = ints(line.split("|", 1)[1].split(","), 2)
                    if not 30 <= a[0] <= 20000 or a[1] <= 0:
                        return "ERR|RANGE|BEEP"
                    tone = pwmio.PWMOut(board.GP6, duty_cycle=0, frequency=a[0], variable_frequency=True)
                    try:
                        tone.duty_cycle = 32768
                        time.sleep(a[1] / 1000)
                    finally:
                        tone.duty_cycle = 0
                        tone.deinit()
                    return "OK|BEEP"
                except Exception:
                    return "ERR|BUZZER|BEEP"
            ''' if fn.endswith('.cs') else '''if line.startswith("BEEP|"):
        try:
            import pwmio
            a = ints(line.split("|", 1)[1].split(","), 2)
            if not 30 <= a[0] <= 20000 or a[1] <= 0:
                return "ERR|RANGE|BEEP"
            tone = pwmio.PWMOut(board.GP6, duty_cycle=0, frequency=a[0], variable_frequency=True)
            try:
                tone.duty_cycle = 32768
                time.sleep(a[1] / 1000)
            finally:
                tone.duty_cycle = 0
                tone.deinit()
            return "OK|BEEP"
        except Exception:
            return "ERR|BUZZER|BEEP"
    '''
    s=s.replace(marker,indent+host+marker.lstrip(),1)
    p.write_text(s,encoding='utf-8')

# Regression coverage.
p=Path('tests/TestRunner.cs'); s=p.read_text(encoding='utf-8')
marker='        // (c) meta guard: every version PIN in this file matches the current release.\n'
if s.count(marker)!=1: raise SystemExit('TestRunner insertion marker not found')
tests='''        // custom GP6 buzzer: replaces only insertion UI; legacy playAudio remains loadable.
        var buzDef = StepDefinitions.Get("buzzer");
        var buzCustom = new Dictionary<string, object?> { ["preset"] = "custom", ["pattern"] = "900:150,80;1200:250" };
        Assert(buzDef.Label == "Buzzer Beep" && StepDefinitions.Get("playAudio").Label == "Play Audio",
            "custom buzzer: new action exists and legacy playAudio remains registered");
        Assert(StepDefinitions.BuildBuzzerCommands(buzCustom).SequenceEqual(new[] { "BEEP|900,150", "DLY|80", "BEEP|1200,250" }),
            "custom buzzer: custom sequence compiles to BEEP/DLY commands");
        bool badBuzzer = false;
        try { StepDefinitions.BuildBuzzerCommands(new Dictionary<string, object?> { ["preset"]="custom", ["pattern"]="25000:10" }); }
        catch (FormatException) { badBuzzer = true; }
        Assert(badBuzzer, "custom buzzer: out-of-range frequency is rejected");
        Assert(p58xaml.Contains("CommandParameter=\\\"buzzer\\\"") && !p58xaml.Contains("CommandParameter=\\\"playAudio\\\""),
            "custom buzzer: all insertion surfaces use buzzer instead of Play Audio");
        var buzFw = V27ReadSrc(Path.Combine("Services", "PicoFirmwareExporter.cs"));
        Assert(buzFw.Contains("PWMOut(board.GP6") && !buzFw.Contains("PWMOut(board.GP5") && !buzFw.Contains("board.D9"),
            "custom buzzer: passive PWM is Pico GP6 only");

'''
s=s.replace(marker,tests+marker)
p.write_text(s,encoding='utf-8')

Path('docs/custom-gp6-buzzer.md').write_text('''# Custom GP6 buzzer step

`Buzzer Beep` replaces `Play Audio` in the insertion UI. Existing `playAudio` rows remain readable and executable in PC mode for backward compatibility.

The buzzer is passive and is driven only by Pico `GP6` through the hardware contract in issue #32. Presets are `short`, `double`, `warning`, `success`, and `custom`.

Custom syntax is `frequency:duration,pause;frequency:duration` in Hz/ms, for example `900:150,80;1200:250`. Each tone exports as `BEEP|freq,ms`; pauses export as `DELAY|ms`. Valid frequencies are 30–20000 Hz.
''',encoding='utf-8')

Path('.github/workflows/apply-custom-buzzer.yml').unlink()
Path('tools/apply_custom_buzzer.py').unlink()
