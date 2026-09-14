from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def edit(rel: str, transform):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    updated = transform(text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    print(f"updated {rel}")
    return True


def add_once(text: str, needle: str, replacement: str, label: str) -> str:
    if replacement in text:
        return text
    if needle not in text:
        raise RuntimeError(f"anchor not found: {label}")
    return text.replace(needle, needle + replacement, 1)


def patch_step_definitions(text: str) -> str:
    # The executor is a global Options setting. Per-action dropdowns duplicated that setting
    # and were the extra section highlighted in the screenshots.
    lines = [line for line in text.splitlines(keepends=True) if 'new("keyboardBoard"' not in line]
    return "".join(lines)


def patch_main_xaml(text: str) -> str:
    # Make the new atomic action the only keyboard press/release entry point.
    if "CommandParameter=\"keyHold\"" not in text:
        pattern = re.compile(
            r'(?ms)(?P<indent>^[ \t]*)<MenuItem Header="Key Down".*?/>[ \t]*\n'
            r'(?P<indent2>^[ \t]*)<MenuItem Header="Key Up".*?/>'
        )

        def key_hold(match: re.Match[str]) -> str:
            block = match.group(0)
            down = re.search(r'(?ms)^[ \t]*<MenuItem Header="Key Down".*?/>', block)
            if not down:
                raise RuntimeError("Key Down menu block not found")
            return down.group(0).replace('Header="Key Down"', 'Header="Key Hold Group"').replace(
                'CommandParameter="keyDown"', 'CommandParameter="keyHold"'
            )

        text, count = pattern.subn(key_hold, text)
        if count == 0:
            raise RuntimeError("no Key Down/Key Up menu pair found")

    # Main has its own recovery-call action; Launch remains available in Launch only.
    if "Header=\"Run/Call Main DC Recovery\"" not in text:
        pattern = re.compile(r'(?ms)^(?P<indent>[ \t]*)<MenuItem Header="Run/Call Launch DC Recovery".*?/>')
        matches = list(pattern.finditer(text))
        if not matches:
            raise RuntimeError("Launch DC Recovery menu item not found")

        def recovery_pair(match: re.Match[str]) -> str:
            launch = match.group(0)
            main = launch.replace("callLaunchDcRecovery", "callMainDcRecovery")
            main = main.replace("Launch", "Main").replace("launch", "main")
            return launch + "\n" + match.group("indent") + main.lstrip()

        text = pattern.sub(recovery_pair, text)

    # Play Options is reparented by MainWindow.AutoCycleUi into this stable inspector slot.
    if 'x:Name="InspectorExtras"' not in text:
        needle = '''<ui:Button Content="بازکردن دیالوگ استپ…" Appearance="Secondary" Margin="0,16,0,0"
                               Command="{Binding EditSelectedCommand}" />'''
        replacement = '''
                    <StackPanel x:Name="InspectorExtras" Margin="0,14,0,0" />'''
        text = add_once(text, needle, replacement, "InspectorExtras")
    return text


def patch_options_xaml(text: str) -> str:
    old = '<Button Content="اندازه‌گیری از دست من…" Click="Calibrate_Click" Padding="10,4" />'
    new = '''<Button Content="ساختن پروفایل دست…" Click="Calibrate_Click" Padding="10,4"
                            ToolTip="۲۰ ثانیه حرکت واقعی موس و تایپ را اندازه می‌گیرد و پیش‌فرض‌های شخصی می‌سازد." />'''
    if old in text:
        text = text.replace(old, new, 1)
    return text


def patch_pipeline_tabs(text: str) -> str:
    if "public bool IsMainPipeline" not in text:
        text = text.replace(
            '    public bool IsLaunchPipeline => _activePipelineTab?.Kind == PipelineKind.Launch;\n',
            '    public bool IsLaunchPipeline => _activePipelineTab?.Kind == PipelineKind.Launch;\n'
            '    public bool IsMainPipeline => _activePipelineTab?.Kind == PipelineKind.Main;\n',
            1,
        )
    text = text.replace(
        '        OnPropertyChanged(nameof(IsLaunchPipeline));\n',
        '        OnPropertyChanged(nameof(IsLaunchPipeline));\n        OnPropertyChanged(nameof(IsMainPipeline));\n',
    )
    return text


def patch_main_vm(text: str) -> str:
    old_guard = '''        if (type == RecoveryCallStepDefinitions.CallLaunch && !IsLaunchPipeline)

        {

            Log("add blocked: Run/Call Launch DC Recovery is only valid in the Launch tab");

            return;

        }
'''
    new_guard = '''        if (type == "keyDown") type = RecoveryCallStepDefinitions.KeyHold;
        if (type == "keyUp")
        {
            Log("add blocked: Key Up is created automatically with Key Hold Group");
            return;
        }

        if (type == RecoveryCallStepDefinitions.CallLaunch && !IsLaunchPipeline)
        {
            Log("add blocked: Run/Call Launch DC Recovery is only valid in the Launch tab");
            return;
        }
        if (type == RecoveryCallStepDefinitions.CallMain && !IsMainPipeline)
        {
            Log("add blocked: Run/Call Main DC Recovery is only valid in the Main tab");
            return;
        }
'''
    if old_guard in text:
        text = text.replace(old_guard, new_guard, 1)
    elif 'type == "keyDown") type = RecoveryCallStepDefinitions.KeyHold' not in text:
        raise RuntimeError("AddStep recovery guard not found")

    if "private bool NormalizeKeyPairs()" not in text:
        anchor = '    private void Renumber()\n\n    {\n'
        method = r'''    private bool NormalizeKeyPairs()
    {
        bool changed = false;
        foreach (var root in Steps.ToList())
            changed |= NormalizeKeyList(root.Parent?.Children ?? Steps);
        return changed;

        bool NormalizeKeyList(IList<StepNode> list)
        {
            bool local = false;
            for (int i = 0; i < list.Count; i++)
            {
                var current = list[i];
                local |= NormalizeKeyList(current.Children);

                if (current.Type == "keyUp")
                {
                    // A release without an owned press is unsafe and cannot be moved into
                    // a valid group. Drop it during migration rather than leaving a stuck state.
                    list.RemoveAt(i--);
                    local = true;
                    continue;
                }
                if (current.Type != "keyDown") continue;

                string key = PropEx.GetString(current.Props, "key", "SHIFT");
                var open = new List<string> { key };
                int close = -1;
                for (int j = i + 1; j < list.Count; j++)
                {
                    var candidate = list[j];
                    if (candidate.Type == "keyDown")
                    {
                        open.Add(PropEx.GetString(candidate.Props, "key", "SHIFT"));
                    }
                    else if (candidate.Type == "keyUp" && open.Count > 0)
                    {
                        string released = PropEx.GetString(candidate.Props, "key", "SHIFT");
                        int matching = open.LastIndexOf(released);
                        if (matching >= 0) open.RemoveAt(matching);
                        if (open.Count == 0) { close = j; break; }
                    }
                }
                if (close < 0) continue;

                var middle = new List<StepNode>();
                for (int j = i + 1; j < close; j++) middle.Add(list[j]);
                // Normalize nested holds before placing them inside the outer transaction.
                local |= NormalizeKeyList(middle);

                var group = new StepNode
                {
                    Type = RecoveryCallStepDefinitions.KeyHold,
                    Name = current.Name,
                    Delay = current.Delay,
                    DelayMax = current.DelayMax,
                    Parent = current.Parent,
                    Props = new Dictionary<string, object?> { ["key"] = key },
                };
                foreach (var child in middle)
                {
                    DocumentService.FixParents(child, group);
                    group.Children.Add(child);
                }
                for (int j = close; j >= i; j--) list.RemoveAt(j);
                list.Insert(i, group);
                local = true;
            }
            return local;
        }
    }

'''
        if anchor not in text:
            raise RuntimeError("Renumber anchor not found")
        text = text.replace(anchor, method + anchor, 1)

    if '        if (NormalizeKeyPairs())' not in text:
        text = text.replace(anchor, '    private void Renumber()\n\n    {\n        if (NormalizeKeyPairs()) _dirty = true;\n', 1)
    return text


def patch_auto_cycle_ui(text: str) -> str:
    if "MovePlayOptionsToInspector" not in text:
        needle = '        var advanced = AutoCycleUiKit.EnsureAdvancedPanel(body);\n'
        text = add_once(text, needle, '        MovePlayOptionsToInspector(window, body);\n', "Play Options move")
        method = r'''    private static void MovePlayOptionsToInspector(MainWindow window, StackPanel body)
    {
        if (window.FindName("InspectorExtras") is not StackPanel host) return;
        Border? owner = null;
        for (DependencyObject? p = body; p is not null; p = VisualTreeHelper.GetParent(p))
            if (p is Border border) { owner = border; break; }
        if (owner is null || owner.Parent is not Panel oldParent || host.Children.Contains(owner)) return;
        oldParent.Children.Remove(owner);
        owner.Margin = new Thickness(0, 0, 0, 8);
        host.Children.Add(owner);
    }

'''
        anchor = '    private static FrameworkElement BuildRangeRow(\n'
        if anchor not in text:
            raise RuntimeError("AutoCycle BuildRangeRow anchor not found")
        text = text.replace(anchor, method + anchor, 1)
    return text


def patch_run_engine(text: str) -> str:
    if 'case "keyHold":' not in text:
        needle = '''                case "forLoop":
                    await RunLoopAsync(s, ct);
                    break;
'''
        replacement = '''                case "keyHold":
                    await RunKeyHoldAsync(s, ct);
                    break;

''' + needle
        if needle not in text:
            raise RuntimeError("RunEngine loop switch anchor not found")
        text = text.replace(needle, replacement, 1)
    if "private async Task RunKeyHoldAsync" not in text:
        anchor = '    private async Task RunLoopAsync(StepNode s, CancellationToken ct)\n'
        method = r'''    private async Task RunKeyHoldAsync(StepNode s, CancellationToken ct)
    {
        string key = PropEx.GetString(s.Props, "key", "SHIFT");
        int vk = KeyMap.VK.TryGetValue(key, out var mapped) ? mapped : 16;
        await Send($"KDOWN|{vk}", ct);
        try
        {
            await RunStepsAsync(s.Children, ct);
        }
        finally
        {
            // The release is unconditional: cancellation, a failed child, or a nested
            // group must never leave the physical key held down.
            try { await Send($"KUP|{vk}", CancellationToken.None); } catch { }
        }
    }

'''
        if anchor not in text:
            raise RuntimeError("RunEngine loop method anchor not found")
        text = text.replace(anchor, method + anchor, 1)
    return text


def main() -> None:
    edit("ams-shell/src/Ams.UI/Models/StepDefinitions.cs", patch_step_definitions)
    edit("ams-shell/src/Ams.UI/MainWindow.xaml", patch_main_xaml)
    edit("ams-shell/src/Ams.UI/Views/OptionsDialog.xaml", patch_options_xaml)
    edit("ams-shell/src/Ams.UI/ViewModels/MainViewModel.PipelineTabs.cs", patch_pipeline_tabs)
    edit("ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs", patch_main_vm)
    edit("ams-shell/src/Ams.UI/MainWindow.AutoCycleUi.cs", patch_auto_cycle_ui)
    edit("ams-shell/src/Ams.UI/Services/RunEngine.cs", patch_run_engine)


if __name__ == "__main__":
    main()
