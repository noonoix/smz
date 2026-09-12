from pathlib import Path


def replace_once(path, old, new):
    p=Path(path); text=p.read_text(encoding='utf-8'); count=text.count(old)
    if count!=1: raise SystemExit(f'expected one match in {path}, got {count}: {old[:100]!r}')
    p.write_text(text.replace(old,new),encoding='utf-8')

xaml='ams-shell/src/Ams.UI/MainWindow.xaml'

# Main Insert menu: expose the existing real pipeline call while editing Launch.
replace_once(xaml,
'''                <MenuItem Header="_Go To Label" Command="{Binding AddStepCommand}" CommandParameter="gotoLabel" />
                <Separator />
                <MenuItem Header="Co_mment" Command="{Binding AddStepCommand}" CommandParameter="comment" />
''',
'''                <MenuItem Header="_Go To Label" Command="{Binding AddStepCommand}" CommandParameter="gotoLabel" />
                <MenuItem Header="Run/Call _Launch DC Recovery" Command="{Binding AddStepCommand}"
                          CommandParameter="callLaunchDcRecovery" IsEnabled="{Binding IsLaunchPipeline}"
                          ToolTip="فقط در تب Launch: اجرای launch_recovery.txt و سپس ادامه‌ی مسیر لانچر" />
                <Separator />
                <MenuItem Header="Co_mment" Command="{Binding AddStepCommand}" CommandParameter="comment" />
''')

# Right-click Add Action menu.
replace_once(xaml,
'''                            <MenuItem Header="Go To Label" CommandParameter="gotoLabel"
                                      Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                            <Separator />
                            <MenuItem Header="Comment" CommandParameter="comment"
''',
'''                            <MenuItem Header="Go To Label" CommandParameter="gotoLabel"
                                      Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                            <MenuItem Header="Run/Call Launch DC Recovery" CommandParameter="callLaunchDcRecovery"
                                      IsEnabled="{Binding PlacementTarget.DataContext.IsLaunchPipeline, RelativeSource={RelativeSource AncestorType=ContextMenu}}"
                                      ToolTip="فقط در تب Launch: اجرای launch_recovery.txt"
                                      Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                            <Separator />
                            <MenuItem Header="Comment" CommandParameter="comment"
''')

# Left rail Flow submenu.
replace_once(xaml,
'''                                    <MenuItem Header="Go To Label" CommandParameter="gotoLabel"
                                              Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                                </ContextMenu>
''',
'''                                    <MenuItem Header="Go To Label" CommandParameter="gotoLabel"
                                              Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                                    <Separator />
                                    <MenuItem Header="Run/Call Launch DC Recovery" CommandParameter="callLaunchDcRecovery"
                                              IsEnabled="{Binding PlacementTarget.DataContext.IsLaunchPipeline, RelativeSource={RelativeSource AncestorType=ContextMenu}}"
                                              ToolTip="فقط در تب Launch: اجرای launch_recovery.txt"
                                              Command="{Binding PlacementTarget.DataContext.AddStepCommand, RelativeSource={RelativeSource AncestorType=ContextMenu}}" />
                                </ContextMenu>
''')

pipeline='ams-shell/src/Ams.UI/ViewModels/MainViewModel.PipelineTabs.cs'
replace_once(pipeline,
'''    public PipelineTabDocument? ActivePipelineTab => _activePipelineTab;
    public string ActivePipelineTitle => _activePipelineTab?.Title ?? "Main";
''',
'''    public PipelineTabDocument? ActivePipelineTab => _activePipelineTab;
    public string ActivePipelineTitle => _activePipelineTab?.Title ?? "Main";
    public bool IsLaunchPipeline => _activePipelineTab?.Kind == PipelineKind.Launch;
''')
# Notify all four state-change sites.
p=Path(pipeline); text=p.read_text(encoding='utf-8')
old='''        OnPropertyChanged(nameof(ActivePipelineTitle));'''
new='''        OnPropertyChanged(nameof(ActivePipelineTitle));
        OnPropertyChanged(nameof(IsLaunchPipeline));'''
count=text.count(old)
if count!=4: raise SystemExit(f'expected four pipeline notification sites, got {count}')
p.write_text(text.replace(old,new),encoding='utf-8')

# Defense in depth: a stale menu or shortcut cannot insert the call in the wrong tab.
vm='ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs'
replace_once(vm,
'''    private void AddStep(string type)

    {

        var def = StepDefinitions.Get(type);
''',
'''    private void AddStep(string type)

    {

        if (type == RecoveryCallStepDefinitions.CallLaunch && !IsLaunchPipeline)

        {

            Log("add blocked: Run/Call Launch DC Recovery is only valid in the Launch tab");

            return;

        }

        var def = StepDefinitions.Get(type);
''')

# Deterministic regression: definition exists and tab-state exposure follows the selected pipeline.
test='tests/TestRunner.cs'
replace_once(test,
'''        def = StepDefinitions.Get("playScript");
        Assert(def.Label == "Play Script (.amsj)", "playScript definition exists");

        // ── Step 2: Commands generation ──────────────────────────────
''',
'''        def = StepDefinitions.Get("playScript");
        Assert(def.Label == "Play Script (.amsj)", "playScript definition exists");

        var launchRecoveryDef = StepDefinitions.Get("callLaunchDcRecovery");
        Assert(launchRecoveryDef.Label == "Run/Call Launch DC Recovery" && launchRecoveryDef.Fields.Count == 0,
            "Launch DC Recovery call is a first-class zero-configuration action");
        var launchActionVm = new MainViewModel();
        launchActionVm.InitializePipelineTabs();
        Assert(!launchActionVm.IsLaunchPipeline, "Launch recovery action is disabled outside the Launch tab");
        var launchTab = launchActionVm.PipelineTabs.Single(t => t.Kind == PipelineKind.Launch);
        launchActionVm.SwitchPipelineCommand.Execute(launchTab);
        Assert(launchActionVm.IsLaunchPipeline, "Launch recovery action becomes available in the Launch tab");

        // ── Step 2: Commands generation ──────────────────────────────
''')

Path('docs/launch-recovery-action.md').write_text('''# Launch DC Recovery action\n\nWhile authoring the **Launch** pipeline tab, the Flow actions now expose **Run/Call Launch DC Recovery** in all three insertion surfaces: the Insert menu, the left-rail submenu, and the step-list right-click menu.\n\nThe action uses the existing `callLaunchDcRecovery` pipeline contract. Export converts it to `INCLUDE|file=launch_recovery.txt`; it is an execution transfer, not an editor-tab switch. The item is disabled outside the Launch tab, and the view model also rejects stale or programmatic insertion in another tab.\n''',encoding='utf-8')

Path('.github/workflows/apply-launch-recovery-action.yml').unlink()
Path('.github/scripts/apply_launch_recovery_action.py').unlink()
