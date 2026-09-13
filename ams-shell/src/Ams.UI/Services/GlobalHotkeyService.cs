using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;

namespace Ams.UI.Services;

/// <summary>
/// OS-level global playback hotkeys. RegisterHotKey remains the preferred path. Some Windows
/// installations or controller utilities reserve a numpad key and make RegisterHotKey fail;
/// those gestures now receive a WH_KEYBOARD_LL fallback instead of silently becoming local-only.
/// </summary>
public static class GlobalHotkeyService
{
    private const int WM_HOTKEY = 0x0312;
    private const int WM_KEYDOWN = 0x0100, WM_KEYUP = 0x0101;
    private const int WM_SYSKEYDOWN = 0x0104, WM_SYSKEYUP = 0x0105;
    private const int WH_KEYBOARD_LL = 13;
    private const int MOD_ALT = 0x1, MOD_CTRL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8;
    private const int MOD_NOREPEAT = 0x4000;
    private const int HKID_RUNSTOP = 0x1001, HKID_PAUSERESUME = 0x1002;

    private static readonly Dictionary<int, string> _idToName = new();
    private static readonly Dictionary<string, (int Mods, uint Vk)> _fallbackGestures = new();
    private static readonly HashSet<uint> _fallbackPressed = new();
    private static readonly List<string> _lastErrors = new();
    private static Func<string, ICommand?>? _getCommand;
    private static HwndSource? _source;
    private static HwndSourceHook? _hook;
    private static IntPtr _hwnd;
    private static IntPtr _keyboardHook;
    private static LowLevelKeyboardProc? _keyboardProc;

    public static IReadOnlyList<string> LastErrors => _lastErrors;
    public static bool IsInstalled => _hwnd != IntPtr.Zero && _source is not null;
    public static bool IsLowLevelFallbackActive => _keyboardHook != IntPtr.Zero;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, int fsModifiers, uint vk);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc callback, IntPtr module, uint threadId);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnhookWindowsHookEx(IntPtr hook);
    [DllImport("user32.dll")]
    private static extern IntPtr CallNextHookEx(IntPtr hook, int code, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern short GetAsyncKeyState(int virtualKey);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr GetModuleHandle(string? moduleName);

    private delegate IntPtr LowLevelKeyboardProc(int code, IntPtr wParam, IntPtr lParam);

    public static void Install(Window window)
    {
        if (_source is not null || _hwnd != IntPtr.Zero) Uninstall();
        _hwnd = new WindowInteropHelper(window).Handle;
        _source = HwndSource.FromHwnd(_hwnd);
        _hook = WndProc;
        _source?.AddHook(_hook);
    }

    public static void Uninstall()
    {
        UnregisterAll();
        if (_source is not null && _hook is not null) _source.RemoveHook(_hook);
        _source = null;
        _hook = null;
        _hwnd = IntPtr.Zero;
        _getCommand = null;
    }

    /// <summary>
    /// Registers the paired playback hotkeys. The returned names are truly global: either owned
    /// by RegisterHotKey or covered by the low-level fallback. Only gestures that fail both paths
    /// are omitted so the caller may install a local binding.
    /// </summary>
    public static HashSet<string> Register(AppSettings settings, Func<string, ICommand?> getCommand)
    {
        UnregisterAll();
        _lastErrors.Clear();
        _getCommand = getCommand;
        var ok = new HashSet<string>();
        if (_hwnd == IntPtr.Zero || _source is null)
        {
            _lastErrors.Add("window handle/message hook is not ready");
            return ok;
        }

        foreach (var (name, gesture, id) in new[]
        {
            ("runstop", settings.RunStopHotkey, HKID_RUNSTOP),
            ("pauseresume", settings.PauseResumeHotkey, HKID_PAUSERESUME),
        })
        {
            if (string.IsNullOrWhiteSpace(gesture)) continue;
            if (!TryParseGesture(gesture, out var mods, out var vk))
            {
                _lastErrors.Add($"{name} ({gesture}): unsupported/invalid key gesture");
                continue;
            }

            if (RegisterHotKey(_hwnd, id, mods | MOD_NOREPEAT, vk))
            {
                _idToName[id] = name;
                ok.Add(name);
                continue;
            }

            var registerError = Marshal.GetLastWin32Error();
            _fallbackGestures[name] = (mods, vk);
            if (EnsureLowLevelHook())
            {
                ok.Add(name);
                continue;
            }

            _fallbackGestures.Remove(name);
            var fallbackError = Marshal.GetLastWin32Error();
            _lastErrors.Add($"{name} ({gesture}): RegisterHotKey Win32 {registerError}; global fallback Win32 {fallbackError}");
        }
        return ok;
    }

    public static void UnregisterAll()
    {
        if (_hwnd != IntPtr.Zero)
            foreach (var id in _idToName.Keys) UnregisterHotKey(_hwnd, id);
        _idToName.Clear();
        _fallbackGestures.Clear();
        _fallbackPressed.Clear();
        if (_keyboardHook != IntPtr.Zero) UnhookWindowsHookEx(_keyboardHook);
        _keyboardHook = IntPtr.Zero;
        _keyboardProc = null;
    }

    private static bool EnsureLowLevelHook()
    {
        if (_keyboardHook != IntPtr.Zero) return true;
        _keyboardProc = KeyboardProc;
        _keyboardHook = SetWindowsHookEx(WH_KEYBOARD_LL, _keyboardProc, GetModuleHandle(null), 0);
        return _keyboardHook != IntPtr.Zero;
    }

    private static IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && _idToName.TryGetValue(wParam.ToInt32(), out var name))
        {
            handled = true;
            Execute(name);
        }
        return IntPtr.Zero;
    }

    private static IntPtr KeyboardProc(int code, IntPtr wParam, IntPtr lParam)
    {
        if (code >= 0)
        {
            var message = wParam.ToInt32();
            var vk = unchecked((uint)Marshal.ReadInt32(lParam));
            if (message is WM_KEYUP or WM_SYSKEYUP)
            {
                _fallbackPressed.Remove(vk);
            }
            else if (message is WM_KEYDOWN or WM_SYSKEYDOWN && _fallbackPressed.Add(vk))
            {
                var currentMods = CurrentModifiers();
                foreach (var pair in _fallbackGestures)
                    if (pair.Value.Vk == vk && pair.Value.Mods == currentMods)
                        Execute(pair.Key);
            }
        }
        return CallNextHookEx(_keyboardHook, code, wParam, lParam);
    }

    private static void Execute(string name)
    {
        void Run()
        {
            var command = _getCommand?.Invoke(name);
            if (command?.CanExecute(null) == true) command.Execute(null);
        }

        var dispatcher = _source?.Dispatcher;
        if (dispatcher is null) return;
        if (dispatcher.CheckAccess()) Run();
        else dispatcher.BeginInvoke(DispatcherPriority.Send, (Action)Run);
    }

    private static int CurrentModifiers()
    {
        var result = 0;
        if (Down(0x10) || Down(0xA0) || Down(0xA1)) result |= MOD_SHIFT;
        if (Down(0x11) || Down(0xA2) || Down(0xA3)) result |= MOD_CTRL;
        if (Down(0x12) || Down(0xA4) || Down(0xA5)) result |= MOD_ALT;
        if (Down(0x5B) || Down(0x5C)) result |= MOD_WIN;
        return result;
    }

    private static bool Down(int vk) => (GetAsyncKeyState(vk) & 0x8000) != 0;

    public static bool TryParseGesture(string gesture, out int mods, out uint vk)
    {
        mods = 0;
        vk = 0;
        if (string.IsNullOrWhiteSpace(gesture)) return false;
        var parts = gesture.Split('+');
        if (parts.Length == 0 || parts.Any(string.IsNullOrWhiteSpace)) return false;
        for (var i = 0; i < parts.Length - 1; i++)
        {
            var part = parts[i].Trim();
            if (part.Equals("Shift", StringComparison.OrdinalIgnoreCase)) mods |= MOD_SHIFT;
            else if (part.Equals("Ctrl", StringComparison.OrdinalIgnoreCase) || part.Equals("Control", StringComparison.OrdinalIgnoreCase)) mods |= MOD_CTRL;
            else if (part.Equals("Alt", StringComparison.OrdinalIgnoreCase)) mods |= MOD_ALT;
            else if (part.Equals("Win", StringComparison.OrdinalIgnoreCase) || part.Equals("Windows", StringComparison.OrdinalIgnoreCase)) mods |= MOD_WIN;
            else return false;
        }

        var keyName = parts[^1].Trim();
        if (!Enum.TryParse<Key>(keyName, true, out var key) ||
            key is Key.None or Key.System or Key.LeftCtrl or Key.RightCtrl or Key.LeftShift or Key.RightShift or
                Key.LeftAlt or Key.RightAlt or Key.LWin or Key.RWin)
            return false;

        var nativeVk = KeyInterop.VirtualKeyFromKey(key);
        if (nativeVk <= 0) return false;
        vk = unchecked((uint)nativeVk);
        return true;
    }
}
