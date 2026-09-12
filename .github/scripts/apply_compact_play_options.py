from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected one match in {path}, got {text.count(old)}: {old[:80]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")

# Main editor: keep only manual-repeat controls in a collapsed compact surface.
main_xaml = "ams-shell/src/Ams.UI/MainWindow.xaml"
replace_once(main_xaml,
    '<TextBlock x:Name="PlayOptToggleText" Text="▾ گزینه‌های پخش" />',
    '<TextBlock x:Name="PlayOptToggleText" Text="▸ اجرای دستی پیشرفته" />')
replace_once(main_xaml,
    '<StackPanel x:Name="PlayOptBody" Margin="2,4,2,4">',
    '<StackPanel x:Name="PlayOptBody" Margin="2,4,2,4" Visibility="Collapsed">')
replace_once(main_xaml,
'''                        <StackPanel Orientation="Horizontal" Margin="0,6,0,0" VerticalAlignment="Center">
                            <CheckBox Content="وقتی تکرار تمام شد کامپیوتر خاموش شود"
                                      IsChecked="{Binding ShutdownWhenFinished}" Foreground="{StaticResource TextPrimaryBrush}" VerticalContentAlignment="Center" />
                            <CheckBox Content="وقتی اسکریپت متوقف شد پنجره‌ی اصلی فعال نشود"
                                      IsChecked="{Binding NoActivateWhenStopped}" Foreground="{StaticResource TextPrimaryBrush}" Margin="16,0,0,0" VerticalContentAlignment="Center" />
                            <Button Content="ذخیره‌ی لاگ اجرا…" Command="{Binding SaveLogCommand}"
                                    Margin="16,0,0,0" Padding="8,3" FontSize="12" Cursor="Hand" />
                        </StackPanel>
''',
'''                        <TextBlock Text="فقط برای تست دستی تب Main؛ اجرای خودکار از AutoCycle تنظیم می‌شود."
                                   Margin="0,6,0,0" FontSize="11"
                                   Foreground="{StaticResource TextTertiaryBrush}" />
''')
replace_once(main_xaml,
'''                        <Button Content="📋 کپی" Click="CopyAllLog_Click"
                                FontSize="11" Padding="8,1" Margin="6,0,0,0" Cursor="Hand"
                                ToolTip="کپی همه‌ی خطوط لاگ به کلیپبورد" />
''',
'''                        <Button Content="📋 کپی" Click="CopyAllLog_Click"
                                FontSize="11" Padding="8,1" Margin="6,0,0,0" Cursor="Hand"
                                ToolTip="کپی همه‌ی خطوط لاگ به کلیپبورد" />
                        <Button Content="💾 ذخیره…" Command="{Binding SaveLogCommand}"
                                FontSize="11" Padding="8,1" Margin="6,0,0,0" Cursor="Hand"
                                ToolTip="ذخیره‌ی کل لاگ اجرا در فایل" />
''')

# Settings: move window activation behavior out of playback controls.
opt_xaml = "ams-shell/src/Ams.UI/Views/OptionsDialog.xaml"
replace_once(opt_xaml,
'''                <ToggleButton x:Name="TabRoles" Content="تقسیم کار بردها" Padding="10,3"
                              Click="TabRoles_Click"
                              Background="{StaticResource BgElevatedBrush}"
                              BorderBrush="{StaticResource BorderSubtleBrush}"
                              BorderThickness="1" Foreground="{StaticResource TextPrimaryBrush}"
                              Cursor="Hand" Margin="4,0,0,0" />
''',
'''                <ToggleButton x:Name="TabRoles" Content="تقسیم کار بردها" Padding="10,3"
                              Click="TabRoles_Click"
                              Background="{StaticResource BgElevatedBrush}"
                              BorderBrush="{StaticResource BorderSubtleBrush}"
                              BorderThickness="1" Foreground="{StaticResource TextPrimaryBrush}"
                              Cursor="Hand" Margin="4,0,0,0" />
                <ToggleButton x:Name="TabBehavior" Content="رفتار" Padding="10,3"
                              Click="TabBehavior_Click"
                              Background="{StaticResource BgElevatedBrush}"
                              BorderBrush="{StaticResource BorderSubtleBrush}"
                              BorderThickness="1" Foreground="{StaticResource TextPrimaryBrush}"
                              Cursor="Hand" Margin="4,0,0,0" />
''')
replace_once(opt_xaml,
'''            <!-- Hotkeys — auto-capture mode -->
            <StackPanel x:Name="HotkeysPanel" Visibility="Collapsed">
''',
'''            <!-- Behavior -->
            <StackPanel x:Name="BehaviorPanel" Visibility="Collapsed">
                <TextBlock Text="رفتار برنامه" FontWeight="SemiBold" FontSize="14"
                           TextAlignment="Right" Foreground="{StaticResource TextPrimaryBrush}" Margin="0,0,0,8" />
                <CheckBox x:Name="NoActivateWhenStoppedBox"
                          Content="وقتی اسکریپت متوقف شد پنجره‌ی اصلی فعال نشود"
                          Foreground="{StaticResource TextPrimaryBrush}" VerticalContentAlignment="Center" />
                <TextBlock Text="این گزینه فقط رفتار پنجره‌ی برنامه را تغییر می‌دهد و روی AutoCycle یا خروجی پیکو اثر ندارد."
                           TextWrapping="Wrap" TextAlignment="Right" FontSize="11" Margin="0,6,0,0"
                           Foreground="{StaticResource TextTertiaryBrush}" />
            </StackPanel>

            <!-- Hotkeys — auto-capture mode -->
            <StackPanel x:Name="HotkeysPanel" Visibility="Collapsed">
''')

opt_cs = "ams-shell/src/Ams.UI/Views/OptionsDialog.xaml.cs"
replace_once(opt_cs,
    '    public string KeyboardBoard { get; private set; } = "pico";\n',
    '    public string KeyboardBoard { get; private set; } = "pico";\n    public bool NoActivateWhenStopped { get; private set; }\n')
replace_once(opt_cs,
    '                         int typeKeyMinMs = 80, int typeKeyMaxMs = 220)\n',
    '                         int typeKeyMinMs = 80, int typeKeyMaxMs = 220,\n                         bool noActivateWhenStopped = false)\n')
replace_once(opt_cs,
    '        KbdPicoRadio.IsChecked = keyboardBoard != "promicro";\n',
    '        KbdPicoRadio.IsChecked = keyboardBoard != "promicro";\n        NoActivateWhenStoppedBox.IsChecked = noActivateWhenStopped;\n        NoActivateWhenStopped = noActivateWhenStopped;\n')
replace_once(opt_cs,
'''        RolesPanel.Visibility = tab == 3 ? Visibility.Visible : Visibility.Collapsed;   // v0.9.45
        TabSerial.IsChecked = tab == 0;
        TabPlayback.IsChecked = tab == 1;
        TabHotkeys.IsChecked = tab == 2;
        TabRoles.IsChecked = tab == 3;
''',
'''        RolesPanel.Visibility = tab == 3 ? Visibility.Visible : Visibility.Collapsed;   // v0.9.45
        BehaviorPanel.Visibility = tab == 4 ? Visibility.Visible : Visibility.Collapsed;
        TabSerial.IsChecked = tab == 0;
        TabPlayback.IsChecked = tab == 1;
        TabHotkeys.IsChecked = tab == 2;
        TabRoles.IsChecked = tab == 3;
        TabBehavior.IsChecked = tab == 4;
''')
replace_once(opt_cs,
    '    private void TabRoles_Click(object sender, RoutedEventArgs e) => SelectTab(3);   // v0.9.45\n',
    '    private void TabRoles_Click(object sender, RoutedEventArgs e) => SelectTab(3);   // v0.9.45\n    private void TabBehavior_Click(object sender, RoutedEventArgs e) => SelectTab(4);\n')
replace_once(opt_cs,
    '        KeyboardBoard = KbdArmRadio.IsChecked == true ? "promicro" : "pico";   // v0.9.44\n',
    '        KeyboardBoard = KbdArmRadio.IsChecked == true ? "promicro" : "pico";   // v0.9.44\n        NoActivateWhenStopped = NoActivateWhenStoppedBox.IsChecked == true;\n')

vm = "ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs"
replace_once(vm,
'''                                      _settings.KeyboardBoard,   // v0.9.44 — which board executes the keyboard

                                      _settings.TypeKeyMinMs, _settings.TypeKeyMaxMs)
''',
'''                                      _settings.KeyboardBoard,   // v0.9.44 — which board executes the keyboard

                                      _settings.TypeKeyMinMs, _settings.TypeKeyMaxMs,

                                      _settings.NoActivateWhenStopped)
''')
replace_once(vm,
'''            _settings.TypeKeyMaxMs = Math.Max(dlg.TypeKeyMinMs, dlg.TypeKeyMaxMs);

            StepDefinitions.TypingFallbackMinMs = _settings.TypeKeyMinMs;           // live update
''',
'''            _settings.TypeKeyMaxMs = Math.Max(dlg.TypeKeyMinMs, dlg.TypeKeyMaxMs);

            _settings.NoActivateWhenStopped = dlg.NoActivateWhenStopped;

            StepDefinitions.TypingFallbackMinMs = _settings.TypeKeyMinMs;           // live update
''')
# Retire the dangerous hidden shutdown action while retaining the legacy JSON property.
p = Path(vm)
text = p.read_text(encoding="utf-8")
pattern = re.compile(r'\n            if \(_settings\.ShutdownWhenFinished\)\n\n            \{\n\n                Log\("⚠ Play Options: shutting down the computer in 30s — cancel with: shutdown /a"\);\n\n                System\.Diagnostics\.Process\.Start\("shutdown", "/s /t 30"\);\n\n            \}\n')
text, count = pattern.subn('\n', text, count=1)
if count != 1:
    raise SystemExit(f"shutdown action match count: {count}")
p.write_text(text, encoding="utf-8")

# Compatibility regression: old settings keys still deserialize even though shutdown is retired from UI/runtime.
test = "tests/TestRunner.cs"
replace_once(test,
'''        Assert(loaded != null && loaded.Port == "COM3" && loaded.ToolkitDir == @"C:\\test\\tk",
            "AppSettings round-trip preserves ToolkitDir");
''',
'''        Assert(loaded != null && loaded.Port == "COM3" && loaded.ToolkitDir == @"C:\\test\\tk",
            "AppSettings round-trip preserves ToolkitDir");
        var legacyPlayback = JsonSerializer.Deserialize<AppSettings>("{\\\"PlayRepeatMode\\\":\\\"times\\\",\\\"PlayRepeatTimes\\\":7,\\\"ShutdownWhenFinished\\\":true,\\\"NoActivateWhenStopped\\\":true}");
        Assert(legacyPlayback != null && legacyPlayback.PlayRepeatMode == "times"
               && legacyPlayback.PlayRepeatTimes == 7 && legacyPlayback.ShutdownWhenFinished
               && legacyPlayback.NoActivateWhenStopped,
            "legacy playback settings still deserialize after the UI cleanup");
''')

Path("docs/manual-playback-options.md").write_text('''# Manual playback options\n\nThe editor keeps manual repeat controls only for deliberate local testing. The surface is named **Advanced manual run** and is collapsed by default so it does not permanently reduce the step list height.\n\n- Normal **Run** uses the selected manual mode; the default remains one pass.\n- Automated restart/resume timing belongs to **AutoCycle** and is not duplicated here.\n- **Do not activate the main window when a script stops** is an application behavior setting under **Options → Behavior**.\n- Saving execution logs lives beside the serial-log clear/copy actions.\n- **Shut down the computer when repetition finishes** is retired from the UI and runtime. The legacy `ShutdownWhenFinished` JSON property remains readable so existing `ams-settings.json` files continue to load safely.\n\nThe legacy repeat properties remain part of exporter contracts; this cleanup does not change PLAN|2 or per-system firmware serialization.\n''', encoding="utf-8")

# Remove the one-shot automation from the final branch diff.
Path(".github/workflows/apply-compact-play-options.yml").unlink()
Path(".github/scripts/apply_compact_play_options.py").unlink()
