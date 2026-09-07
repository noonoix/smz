using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;

namespace Ams.UI.Services;

/// <summary>
/// v0.9.3 — OS-level global hotkeys for Run / Stop / Pause / Resume (fire even when the
/// app window has no focus), via RegisterHotKey + WPF's HwndSource.AddHook.
///
/// STARTUP-CRASH FIX (the v0.9.2 build where "the exe opens and nothing appears"):
/// the previous implementation subclassed the window with SetWindowLongPtr(GWL_WNDPROC)
/// using a delegate whose signature had an extra `ref bool handled` parameter. That
/// `ref bool` is WPF's HwndSourceHook convention — a NATIVE window procedure is
/// LRESULT(HWND, UINT, WPARAM, LPARAM), four parameters. Windows dispatched the very
/// first message (during window creation, before anything was shown) through a function
/// pointer with the wrong signature → stack corruption → the process died instantly.
/// It also never called the previous WndProc and stored the hook's own pointer as
/// "previous". HwndSource.AddHook is the supported, safe WPF mechanism — no p/invoke
/// subclassing at all.
/// </summary>
public static class GlobalHotkeyService
{
    private const int WM_HOTKEY = 0x0312;
    private const int MOD_ALT = 0x1, MOD_CTRL = 0x2, MOD_SHIFT = 0x4, MOD_WIN = 0x8;
    private const int MOD_NOREPEAT = 0x4000; // one action per press even when the keys are held

    private const int HKID_RUNSTOP = 0x1001, HKID_PAUSERESUME = 0x1002;   // paired playback hotkeys

    private static readonly Dictionary<int, string> _idToName = new();
    private static readonly List<string> _lastErrors = new();
    private static Func<string, ICommand?>? _getCommand;
    private static HwndSource? _source;
    private static HwndSourceHook? _hook;   // kept alive for the whole session
    private static IntPtr _hwnd;

    public static IReadOnlyList<string> LastErrors => _lastErrors;
    public static bool IsInstalled => _hwnd != IntPtr.Zero && _source is not null;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, int fsModifiers, uint vk);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    /// <summary>Install the message hook — call once from MainWindow.OnSourceInitialized
    /// (the window handle exists by then).</summary>
    public static void Install(Window window)
    {
        // Defensive idempotency: SourceInitialized should run once, but never stack hooks if a
        // host recreates the window or Install is accidentally called again.
        if (_source is not null || _hwnd != IntPtr.Zero) Uninstall();
        _hwnd = new WindowInteropHelper(window).Handle;
        _source = HwndSource.FromHwnd(_hwnd);
        _hook = WndProc;
        _source?.AddHook(_hook);   // the supported WPF way — safe, no subclassing
    }

    /// <summary>Remove the hook and every registered hotkey — call from MainWindow.OnClosed.</summary>
    public static void Uninstall()
    {
        UnregisterAll();
        if (_source is not null && _hook is not null) _source.RemoveHook(_hook);
        _source = null;
        _hook = null;
        _hwnd = IntPtr.Zero;
        _getCommand = null;
    }

    /// <summary>(Re)registers the two PAIRED playback hotkeys from settings (v0.9.43 — run/stop share
    /// one key, pause/resume share another; user request, 4 keys → 2). Returns the command
    /// names that are now GLOBAL — the caller skips their window-local InputBindings so a
    /// focused keypress does not fire the command twice. A combo the OS refuses (owned by
    /// another app) keeps its local binding as fallback.</summary>
    public static HashSet<string> Register(AppSettings settings, Func<string, ICommand?> getCommand)
    {
        UnregisterAll();
        _lastErrors.Clear();
        _getCommand = getCommand;
        var ok = new HashSet<string>();
        if (_hwnd == IntPtr.Zero || _source is null)
        {
            _lastErrors.Add("window handle/message hook is not ready");
            return ok;   // local bindings keep working, but the caller now reports why
        }

        foreach (var (name, hk, id) in new[]
        {
            ("runstop", settings.RunStopHotkey, HKID_RUNSTOP),
            ("pauseresume", settings.PauseResumeHotkey, HKID_PAUSERESUME),
        })
        {
            if (string.IsNullOrWhiteSpace(hk)) continue;
            if (!TryParseGesture(hk, out var mods, out var vk))
            {
                _lastErrors.Add($"{name} ({hk}): unsupported/invalid key gesture");
                continue;
            }
            if (RegisterHotKey(_hwnd, id, mods | MOD_NOREPEAT, vk))
            {
                _idToName[id] = name;
                ok.Add(name);
            }
            else
            {
                int error = Marshal.GetLastWin32Error();
                string message;
                try { message = new Win32Exception(error).Message; }
                catch { message = "unknown Windows error"; }
                _lastErrors.Add($"{name} ({hk}): RegisterHotKey failed — Win32 {error}: {message}");
            }
        }
        return ok;
    }

    /// <summary>Unregister everything we registered (safe any time, even after close).</summary>
    public static void UnregisterAll()
    {
        if (_hwnd != IntPtr.Zero)
            foreach (var id in _idToName.Keys) UnregisterHotKey(_hwnd, id);
        _idToName.Clear();
    }

    private static IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && _idToName.TryGetValue(wParam.ToInt32(), out var name))
        {
            handled = true; // this ID belongs to AMS even if the command is currently unavailable
            var cmd = _getCommand?.Invoke(name);
            if (cmd?.CanExecute(null) == true)
                cmd.Execute(null);
        }
        return IntPtr.Zero;   // not ours → normal processing continues
    }

    /// <summary>
    /// Converts the same WPF Key names emitted by OptionsDialog to Win32 virtual-key codes.
    /// v0.9.9 fixes the old F1..F12/A-Z/0-9-only parser which silently rejected the user's
    /// Shift+Add, Shift+Subtract, Ctrl+Add and Ctrl+Multiply numpad shortcuts.
    /// Public for deterministic regression tests; this method does not call user32.
    /// </summary>
    public static bool TryParseGesture(string gesture, out int mods, out uint vk)
    {
        mods = 0; vk = 0;
        if (string.IsNullOrWhiteSpace(gesture)) return false;
        var parts = gesture.Split('+');
        if (parts.Length == 0 || parts.Any(string.IsNullOrWhiteSpace)) return false;
        for (int i = 0; i < parts.Length - 1; i++)
        {
            var p = parts[i].Trim();
            if (p.Equals("Shift", StringComparison.OrdinalIgnoreCase)) mods |= MOD_SHIFT;
            else if (p.Equals("Ctrl", StringComparison.OrdinalIgnoreCase) ||
                     p.Equals("Control", StringComparison.OrdinalIgnoreCase)) mods |= MOD_CTRL;
            else if (p.Equals("Alt", StringComparison.OrdinalIgnoreCase)) mods |= MOD_ALT;
            else if (p.Equals("Win", StringComparison.OrdinalIgnoreCase) ||
                     p.Equals("Windows", StringComparison.OrdinalIgnoreCase)) mods |= MOD_WIN;
            else return false;
        }
        string keyName = parts[^1].Trim();
        if (!Enum.TryParse<Key>(keyName, ignoreCase: true, out var key) ||
            key is Key.None or Key.System or Key.LeftCtrl or Key.RightCtrl or Key.LeftShift or
                Key.RightShift or Key.LeftAlt or Key.RightAlt or Key.LWin or Key.RWin)
            return false;

        int nativeVk = KeyInterop.VirtualKeyFromKey(key);
        if (nativeVk <= 0) return false;
        vk = unchecked((uint)nativeVk);
        return true;
    }
}
