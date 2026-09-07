#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    # Check the complete replacement first: some replacements intentionally retain
    # their old anchor as a prefix, so counting old before this check breaks idempotency.
    if new in text:
        return text, False
    count = text.count(old)
    if count == 1:
        return text.replace(old, new, 1), True
    raise SystemExit(f"ERROR: {label}: expected one anchor, found {count}")


def patch_file(path: pathlib.Path, transforms) -> bool:
    if not path.exists():
        raise SystemExit(f"ERROR: missing {path}")
    original = path.read_text(encoding="utf-8")
    text = original
    changed_any = False
    for old, new, label in transforms:
        text, changed = replace_once(text, old, new, label)
        changed_any |= changed
    if changed_any:
        backup = path.with_suffix(path.suffix + ".bak-v0.9.58d")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8", newline="")
        print(f"OK: patched {path}")
    else:
        print(f"already patched: {path}")
    return changed_any


def main() -> int:
    ap = argparse.ArgumentParser(description="Classroom Studio v0.9.58d hotfix")
    ap.add_argument("repo", nargs="?", default=".", help="repository root")
    args = ap.parse_args()
    root = pathlib.Path(args.repo).resolve()

    bridge = root / "ams-shell/bridge/bridge.py"
    hotkeys = root / "ams-shell/src/Ams.UI/Services/GlobalHotkeyService.cs"
    pico = root / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
    window = root / "ams-shell/src/Ams.UI/MainWindow.xaml.cs"
    tests = root / "tests/TestRunner.cs"

    patch_file(bridge, [(
        '                    dlys = [int(d) for d in req.get("dlys", "") if d]',
        '                    dlys = [int(d) for d in req.get("dlys", "").split(";") if d.strip()]',
        "send_path delay parser",
    )])

    patch_file(hotkeys, [
        (
            '    private const int HKID_RUNSTOP = 0x1001, HKID_PAUSERESUME = 0x1002;   // v0.9.43 — paired: 4 hotkeys → 2 (user request)\n'
            '    private const int HKID_HARD_NUMLOCK = 0x1003;   // v0.9.58 — hardware BTN1 on Pico (GP2) → Run/Stop\n'
            '    private const int HKID_HARD_SCROLL = 0x1004;    // v0.9.58 — hardware BTN2 on Pico (GP3) → Pause/Resume\n',
            '    private const int HKID_RUNSTOP = 0x1001, HKID_PAUSERESUME = 0x1002;   // paired playback hotkeys\n',
            "remove fixed keypad hotkey IDs",
        ),
        (
            '            ("runstop", settings.RunStopHotkey, HKID_RUNSTOP),           // v0.9.43 — one key toggles run/stop\n'
            '            ("pauseresume", settings.PauseResumeHotkey, HKID_PAUSERESUME),   // one key toggles pause/resume\n'
            '            // v0.9.58 — hardware keypad always registers NUM_LOCK and SCROLL_LOCK\n'
            '            ("hard_numlock", "Num Lock", HKID_HARD_NUMLOCK),\n'
            '            ("hard_scroll", "Scroll Lock", HKID_HARD_SCROLL),\n',
            '            ("runstop", settings.RunStopHotkey, HKID_RUNSTOP),\n'
            '            ("pauseresume", settings.PauseResumeHotkey, HKID_PAUSERESUME),\n',
            "remove fixed NumLock/ScrollLock registrations",
        ),
    ])

    helper_anchor = '    private static string Escape(string s) => s.Replace("\\\\", "\\\\\\\\").Replace("\\\"", "\\\\\\\"");\n'
    helper_new = helper_anchor + r'''

    /// <summary>Converts an Options hotkey gesture to Win32 VK values that code.py maps to USB HID usages.
    /// Kept independent from RegisterHotKey so the exported Pico exactly follows the saved two gestures.</summary>
    public static int[] HotkeyToVirtualKeys(string? gesture)
    {
        if (string.IsNullOrWhiteSpace(gesture)) return Array.Empty<int>();
        var parts = gesture.Split('+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0) return Array.Empty<int>();
        var result = new List<int>();
        for (int i = 0; i < parts.Length - 1; i++)
        {
            result.Add(parts[i].ToLowerInvariant() switch
            {
                "shift" => 0xA0, "ctrl" or "control" => 0xA2,
                "alt" => 0xA4, "win" or "windows" => 0x5B,
                _ => throw new InvalidDataException("unsupported Pico hotkey modifier: " + parts[i]),
            });
        }
        string key = parts[^1];
        int vk;
        if (key.Length == 1 && char.IsLetter(key[0])) vk = char.ToUpperInvariant(key[0]);
        else if (key.Length == 1 && char.IsDigit(key[0])) vk = key[0];
        else if (key.Length == 2 && (key[0] == 'D' || key[0] == 'd') && char.IsDigit(key[1])) vk = key[1];
        else if (key.StartsWith("F", StringComparison.OrdinalIgnoreCase)
                 && int.TryParse(key[1..], out int fn) && fn is >= 1 and <= 24) vk = 0x70 + fn - 1;
        else if (key.StartsWith("NumPad", StringComparison.OrdinalIgnoreCase)
                 && int.TryParse(key[6..], out int np) && np is >= 0 and <= 9) vk = 0x60 + np;
        else vk = key.ToLowerInvariant() switch
        {
            "back" or "backspace" => 0x08, "tab" => 0x09, "clear" => 0x0C,
            "enter" or "return" => 0x0D, "pause" => 0x13, "capslock" => 0x14,
            "escape" => 0x1B, "space" => 0x20, "pageup" => 0x21, "pagedown" => 0x22,
            "end" => 0x23, "home" => 0x24, "left" => 0x25, "up" => 0x26,
            "right" => 0x27, "down" => 0x28, "printscreen" => 0x2C,
            "insert" => 0x2D, "delete" => 0x2E, "scroll" or "scrolllock" => 0x91,
            "multiply" => 0x6A, "add" => 0x6B, "subtract" => 0x6D,
            "decimal" => 0x6E, "divide" => 0x6F,
            "oemplus" => 0xBB, "oemcomma" => 0xBC, "oemminus" => 0xBD,
            "oemperiod" => 0xBE, "oemquestion" => 0xBF, "oemtilde" => 0xC0,
            "oemopenbrackets" => 0xDB, "oempipe" => 0xDC,
            "oemclosebrackets" => 0xDD, "oemquotes" => 0xDE,
            _ => throw new InvalidDataException("unsupported Pico hotkey key: " + key),
        };
        result.Add(vk);
        return result.ToArray();
    }

    private static string HotkeyTuple(string? gesture)
    {
        var values = HotkeyToVirtualKeys(gesture);
        if (values.Length == 0) return "()";
        return "(" + string.Join(", ", values) + (values.Length == 1 ? "," : "") + ")";
    }
'''

    build_old = '''    public static string BuildCodePy(IReadOnlyList<LightState> states, string machine,
        string loopMode = "forever", int loopCount = 0, int loopSeconds = 0, bool keyboardOnArm = false)
        => CodeTemplate
            .Replace("__MACHINE__", machine)
            .Replace("__GENERATED__", DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture))
            .Replace("__VERSION__", BundleVersion)
            .Replace("__STATE_COUNT__", states.Count.ToString(CultureInfo.InvariantCulture))
            .Replace("__LOOP_MODE__", loopMode)                                                    // v0.9.44
            .Replace("__LOOP_COUNT__", loopCount.ToString(CultureInfo.InvariantCulture))           // v0.9.44
            .Replace("__LOOP_SECONDS__", loopSeconds.ToString(CultureInfo.InvariantCulture))       // v0.9.44
            .Replace("__KBD_ON_ARM__", keyboardOnArm ? "True" : "False");                          // v0.9.44
'''
    build_new = '''    public static string BuildCodePy(IReadOnlyList<LightState> states, string machine,
        string loopMode = "forever", int loopCount = 0, int loopSeconds = 0, bool keyboardOnArm = false,
        string? runStopHotkey = "Shift+F1", string? pauseResumeHotkey = "Shift+F3")
        => CodeTemplate
            .Replace("__MACHINE__", machine)
            .Replace("__GENERATED__", DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture))
            .Replace("__VERSION__", BundleVersion)
            .Replace("__STATE_COUNT__", states.Count.ToString(CultureInfo.InvariantCulture))
            .Replace("__LOOP_MODE__", loopMode)
            .Replace("__LOOP_COUNT__", loopCount.ToString(CultureInfo.InvariantCulture))
            .Replace("__LOOP_SECONDS__", loopSeconds.ToString(CultureInfo.InvariantCulture))
            .Replace("__KBD_ON_ARM__", keyboardOnArm ? "True" : "False")
            .Replace("__RUNSTOP_HOTKEY__", HotkeyTuple(runStopHotkey))
            .Replace("__PAUSERESUME_HOTKEY__", HotkeyTuple(pauseResumeHotkey));
'''

    constants_old = '''        KBD_ON_ARM = __KBD_ON_ARM__

        SPECIAL_VK = {
'''
    constants_new = '''        KBD_ON_ARM = __KBD_ON_ARM__
        # v0.9.58d — BTN1/BTN2 emit the exact gestures saved in Classroom Studio Options.
        RUNSTOP_HOTKEY = __RUNSTOP_HOTKEY__
        PAUSERESUME_HOTKEY = __PAUSERESUME_HOTKEY__

        SPECIAL_VK = {
'''

    button_helper_anchor = '''        def press(vk, hold_ms):
            code = keycode_for_vk(vk)
            kbd.press(code)
            time.sleep(max(10, hold_ms) / 1000)
            kbd.release(code)


'''
    button_helper_new = button_helper_anchor + '''        # Win32 VK -> USB HID usage. This covers every key Options currently accepts.
        HOTKEY_VK_TO_HID = {
            0x08: 0x2A, 0x09: 0x2B, 0x0C: 0x9C, 0x0D: 0x28,
            0x13: 0x48, 0x14: 0x39, 0x1B: 0x29, 0x20: 0x2C,
            0x21: 0x4B, 0x22: 0x4E, 0x23: 0x4D, 0x24: 0x4A,
            0x25: 0x50, 0x26: 0x52, 0x27: 0x4F, 0x28: 0x51,
            0x2C: 0x46, 0x2D: 0x49, 0x2E: 0x4C, 0x5B: 0xE3,
            0x5C: 0xE7, 0x6A: 0x55, 0x6B: 0x57, 0x6D: 0x56,
            0x6E: 0x63, 0x6F: 0x54, 0x91: 0x47,
            0xA0: 0xE1, 0xA1: 0xE5, 0xA2: 0xE0, 0xA3: 0xE4,
            0xA4: 0xE2, 0xA5: 0xE6,
            0xBB: 0x2E, 0xBC: 0x36, 0xBD: 0x2D, 0xBE: 0x37,
            0xBF: 0x38, 0xC0: 0x35, 0xDB: 0x2F, 0xDC: 0x31,
            0xDD: 0x30, 0xDE: 0x34,
        }

        def hotkey_hid(vk):
            if 0x41 <= vk <= 0x5A:
                return 0x04 + vk - 0x41
            if 0x31 <= vk <= 0x39:
                return 0x1E + vk - 0x31
            if vk == 0x30:
                return 0x27
            if 0x70 <= vk <= 0x7B:
                return 0x3A + vk - 0x70
            if 0x7C <= vk <= 0x87:
                return 0x68 + vk - 0x7C
            if 0x60 <= vk <= 0x69:
                return 0x62 if vk == 0x60 else 0x59 + vk - 0x61
            return HOTKEY_VK_TO_HID.get(vk)

        def send_hotkey(vks):
            codes = [hotkey_hid(vk) for vk in vks]
            codes = [code for code in codes if code is not None]
            if not codes:
                return
            for code in codes:
                kbd.press(code)
            time.sleep(0.04)
            for code in reversed(codes):
                kbd.release(code)


'''

    buttons_old = '''                    if b1 and not _last_btn1:
                        kbd.send(Keycode.NUM_LOCK)
                    if b2 and not _last_btn2:
                        kbd.send(Keycode.SCROLL_LOCK)
'''
    buttons_new = '''                    if b1 and not _last_btn1:
                        send_hotkey(RUNSTOP_HOTKEY)
                    if b2 and not _last_btn2:
                        send_hotkey(PAUSERESUME_HOTKEY)
'''

    export_old = '''        Put(string.IsNullOrWhiteSpace(Path.GetFileName(codePyPath)) ? "code.py" : Path.GetFileName(codePyPath), BuildCodePy(states, machine, loopMode, loopCount, loopSeconds, keyboardOnArm));   // v0.9.44
        Put("boot.py", BuildBootPy());
'''
    export_new = '''        var settings = AppSettings.Load();
        Put(string.IsNullOrWhiteSpace(Path.GetFileName(codePyPath)) ? "code.py" : Path.GetFileName(codePyPath),
            BuildCodePy(states, machine, loopMode, loopCount, loopSeconds, keyboardOnArm,
                        settings.RunStopHotkey, settings.PauseResumeHotkey));
        Put("boot.py", BuildBootPy());
'''

    patch_file(pico, [
        (helper_anchor, helper_new, "Pico gesture converter"),
        (build_old, build_new, "BuildCodePy hotkey parameters"),
        (constants_old, constants_new, "code.py hotkey tuples"),
        (button_helper_anchor, button_helper_new, "code.py HID gesture sender"),
        (buttons_old, buttons_new, "Pico button actions"),
        (export_old, export_new, "Export reads saved hotkeys"),
    ])

    loaded_old = '''            vm.ReloadKeyBindings();
            vm.AutoConnectOnStartup();   // v0.9.5 — شناسایی و اتصال خودکار برد
            AttachScopeVeinEvents(vm);
'''
    loaded_new = '''            vm.ReloadKeyBindings();
            vm.AutoConnectOnStartup();   // v0.9.5 — شناسایی و اتصال خودکار برد
            InstallLogClipboardMenu(vm);   // v0.9.58d — selected/all serial log → Windows clipboard
            AttachScopeVeinEvents(vm);
'''
    method_anchor = '''    // ── selection → view model (Extended mode gives Ctrl-toggle / Shift-range natively) ──
'''
    method_new = r'''    private void InstallLogClipboardMenu(MainViewModel vm)
    {
        var logList = FindLogListBox(this, vm.LogLines);
        if (logList is null) return;
        logList.SelectionMode = SelectionMode.Extended;
        var menu = new ContextMenu();
        var selected = new MenuItem { Header = "کپی خطوط انتخاب‌شده" };
        selected.Click += (_, _) => CopyLog(logList.SelectedItems.Cast<string>());
        var all = new MenuItem { Header = "کپی کل لاگ" };
        all.Click += (_, _) => CopyLog(vm.LogLines);
        menu.Items.Add(selected);
        menu.Items.Add(all);
        logList.ContextMenu = menu;
    }

    private static ListBox? FindLogListBox(DependencyObject root, object source)
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            if (child is ListBox list && ReferenceEquals(list.ItemsSource, source)) return list;
            if (FindLogListBox(child, source) is { } nested) return nested;
        }
        return null;
    }

    private static void CopyLog(IEnumerable<string> lines)
    {
        var text = string.Join(Environment.NewLine, lines);
        if (text.Length > 0) Clipboard.SetText(text);
    }

''' + method_anchor
    patch_file(window, [
        (loaded_old, loaded_new, "install log clipboard menu"),
        (method_anchor, method_new, "log clipboard methods"),
    ])

    old_test = '''        // (b) exporter wires NUM_LOCK / SCROLL_LOCK and polls buttons inside main loop
        var p58exp = V27ReadSrc(Path.Combine("Services", "PicoFirmwareExporter.cs"));
        Assert(p58exp.Contains("Keycode.NUM_LOCK") && p58exp.Contains("Keycode.SCROLL_LOCK"),
            "v0.9.58: Pico firmware sends NUM_LOCK (BTN1) and SCROLL_LOCK (BTN2)");
        Assert(p58exp.Contains("btn1") && p58exp.Contains("digitalio.DigitalInOut(board.GP2)"),
            "v0.9.58: keypad button reader on GP2 with pull-up");
'''
    new_test = '''        // (b) v0.9.58d: keypad emits the two gestures saved in Options (no fixed lock keys)
        var p58exp = V27ReadSrc(Path.Combine("Services", "PicoFirmwareExporter.cs"));
        var p58keys = PicoFirmwareExporter.HotkeyToVirtualKeys("Ctrl+Add");
        Assert(p58keys.SequenceEqual(new[] { 0xA2, 0x6B }),
            "v0.9.58d: Pico exporter converts configured modifier + numpad key");
        var p58code = PicoFirmwareExporter.BuildCodePy(new List<PicoFirmwareExporter.LightState>(), "M",
            runStopHotkey: "Shift+F7", pauseResumeHotkey: "Ctrl+Add");
        Assert(p58code.Contains("RUNSTOP_HOTKEY = (160, 118)")
               && p58code.Contains("PAUSERESUME_HOTKEY = (162, 107)"),
            "v0.9.58d: exported code.py bakes the actual Options gestures");
        Assert(p58exp.Contains("send_hotkey(RUNSTOP_HOTKEY)")
               && p58exp.Contains("send_hotkey(PAUSERESUME_HOTKEY)")
               && !p58exp.Contains("kbd.send(Keycode.NUM_LOCK)"),
            "v0.9.58d: Pico buttons no longer emit fixed Num/Scroll Lock keys");
        Assert(p58exp.Contains("btn1") && p58exp.Contains("digitalio.DigitalInOut(board.GP2)"),
            "v0.9.58: keypad button reader on GP2 with pull-up");
        var p58bridge = File.ReadAllText(Path.Combine(V27SrcRoot(), "..", "..", "bridge", "bridge.py"));
        Assert(p58bridge.Contains(".split(\";\") if d.strip()"),
            "v0.9.58d: send_path parses semicolon-delimited delays, not individual characters");
        var p58hotkeys = V27ReadSrc(Path.Combine("Services", "GlobalHotkeyService.cs"));
        Assert(!p58hotkeys.Contains("hard_numlock") && !p58hotkeys.Contains("hard_scroll"),
            "v0.9.58d: fixed lock-key registrations and their startup warnings are gone");
        var p58window = V27ReadSrc("MainWindow.xaml.cs");
        Assert(p58window.Contains("کپی کل لاگ") && p58window.Contains("Clipboard.SetText"),
            "v0.9.58d: serial log has selected/all clipboard copy actions");
'''
    # V27SrcRoot is local inside Main in current runner, so avoid introducing a call if the helper is absent.
    # The bridge assertion is guarded/re-written to use the same walk-up style if needed.
    if tests.exists():
        test_text = tests.read_text(encoding="utf-8")
        if "static string V27SrcRoot()" not in test_text and "string V27SrcRoot()" not in test_text:
            new_test = new_test.replace(
                '        var p58bridge = File.ReadAllText(Path.Combine(V27SrcRoot(), "..", "..", "bridge", "bridge.py"));\n'
                '        Assert(p58bridge.Contains(".split(\\\";\\\") if d.strip()"),\n'
                '            "v0.9.58d: send_path parses semicolon-delimited delays, not individual characters");\n',
                '        var p58bridge = V27ReadSrc(Path.Combine("..", "..", "bridge", "bridge.py"));\n'
                '        Assert(p58bridge.Contains(".split(\\\";\\\") if d.strip()"),\n'
                '            "v0.9.58d: send_path parses semicolon-delimited delays, not individual characters");\n'
            )
        patch_file(tests, [(old_test, new_test, "v0.9.58d regression tests")])

    # Static verification independent of Windows/WPF build.
    b = bridge.read_text(encoding="utf-8")
    h = hotkeys.read_text(encoding="utf-8")
    p = pico.read_text(encoding="utf-8")
    w = window.read_text(encoding="utf-8")
    checks = {
        "send_path delimiter fix": '.split(";") if d.strip()' in b,
        "no fixed lock registrations": "hard_numlock" not in h and "hard_scroll" not in h,
        "configured Pico gestures": "send_hotkey(RUNSTOP_HOTKEY)" in p and "__RUNSTOP_HOTKEY__" in p,
        "copy log menu": "کپی کل لاگ" in w and "Clipboard.SetText" in w,
    }
    failed = [name for name, ok in checks.items() if not ok]
    for name, ok in checks.items(): print(("PASS" if ok else "FAIL") + ": " + name)
    if failed: raise SystemExit("ERROR: verification failed: " + ", ".join(failed))

    print("\nNext:")
    print("  dotnet run --project tests/TestRunner.csproj -c Release")
    print("  dotnet build ams-shell/AMS.sln -c Release")
    print("  Export Pico Firmware again and replace code.py on CIRCUITPY")
    print("  Right-click the serial log -> کپی کل لاگ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
