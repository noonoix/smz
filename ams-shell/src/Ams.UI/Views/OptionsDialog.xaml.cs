using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using WKeyboardDevice = System.Windows.Input.KeyboardDevice;
using WModifiers = System.Windows.Input.ModifierKeys;

namespace Ams.UI.Views;

/// <summary>Options dialog — Serial/Board | Playback | Hotkeys tabs (§v0.8.4–v0.8.5).
/// Hotkey fields use auto-capture: click a field → press key combo → displayed instantly.</summary>
public partial class OptionsDialog : Window
{
    public string Port { get; private set; } = "";
    public string PythonDir { get; private set; } = "";
    public string ToolkitDir { get; private set; } = "";
    public int WordDelayMin { get; private set; } = 0;
    public int WordDelayMax { get; private set; } = 0;
    public bool UseWordHumanize { get; private set; }
    public int MouseMoveSpeedMin { get; private set; } = 300;   // v0.9.24 — recalibrated (was 0 → 150 → 300)
    public int MouseMoveSpeedMax { get; private set; } = 2000;  // v0.9.24 — recalibrated (was 2300 → 500 → 2000)
    public int TypeKeyMinMs { get; private set; } = 80;         // v0.9.23 — from "Measure from my hand"
    public int TypeKeyMaxMs { get; private set; } = 220;
    // v0.9.43 — paired playback hotkeys (user request, 4 keys → 2)
    public string RunStopHotkey { get; private set; } = "Shift+F1";
    public string PauseResumeHotkey { get; private set; } = "Shift+F3";
    // v0.9.44 — which board executes the keyboard ("pico" = brain, "promicro" = arm)
    public string KeyboardBoard { get; private set; } = "pico";
    public bool NoActivateWhenStopped { get; private set; }

    // v0.9.55 - embedded mode: the settings live inside the main window, so this Window is
    // never shown. Its content is detached once and hosted by MainWindow; Ok/Cancel raise
    // Completed instead of setting DialogResult (which only works for a real ShowDialog).
    private bool _embedded;
    public event System.EventHandler<bool>? Completed;

    public System.Windows.UIElement EmbedContent()
    {
        _embedded = true;
        var root = (System.Windows.FrameworkElement)Content;
        Content = null;
        root.PreviewKeyDown += Window_PreviewKeyDown;   // hotkey capture still works off-window
        return root;
    }

    private void Finish(bool accepted)
    {
        if (_embedded) { Completed?.Invoke(this, accepted); return; }
        DialogResult = accepted;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        if (_embedded) Finish(false);
    }

    // Hotkey capture state
    private string? _capturingField = null;
    private bool _captureInProgess = false;
    private ModifierKeys _activeModifier = ModifierKeys.None;

    public OptionsDialog(string port, string pythonDir, string toolkitDir,
                         int wordDelayMin = 0, int wordDelayMax = 0,
                         int mouseMoveSpeedMin = 300, int mouseMoveSpeedMax = 2000,
                         string runStopHotkey = "Shift+F1", string pauseResumeHotkey = "Shift+F3",   // v0.9.43 — paired
                         string keyboardBoard = "pico",   // v0.9.44 — which board executes the keyboard
                         int typeKeyMinMs = 80, int typeKeyMaxMs = 220,
                         bool noActivateWhenStopped = false)
    {
        InitializeComponent();
        PortBox.Text = port;
        DirBox.Text = pythonDir;
        ToolkitBox.Text = toolkitDir;
        WordDelayMinBox.Text = wordDelayMin.ToString();
        WordDelayMaxBox.Text = wordDelayMax.ToString();
        MouseSpeedMinBox.Text = mouseMoveSpeedMin.ToString();
        MouseSpeedMaxBox.Text = mouseMoveSpeedMax.ToString();

        // Set initial hotkey displays (v0.9.43 — paired)
        RunStopHkDisplay.Text = runStopHotkey;
        PauseResumeHkDisplay.Text = pauseResumeHotkey;
        RunStopHotkey = runStopHotkey;
        PauseResumeHotkey = pauseResumeHotkey;
        KeyboardBoard = keyboardBoard;   // v0.9.44
        KbdArmRadio.IsChecked = keyboardBoard == "promicro";
        KbdPicoRadio.IsChecked = keyboardBoard != "promicro";
        NoActivateWhenStoppedBox.IsChecked = noActivateWhenStopped;
        NoActivateWhenStopped = noActivateWhenStopped;

        Port = port;
        PythonDir = pythonDir;
        ToolkitDir = toolkitDir;
        WordDelayMin = wordDelayMin;
        WordDelayMax = wordDelayMax;
        UseWordHumanize = wordDelayMax > wordDelayMin;
        MouseMoveSpeedMin = mouseMoveSpeedMin;
        MouseMoveSpeedMax = mouseMoveSpeedMax;
        TypeKeyMinMs = typeKeyMinMs;
        TypeKeyMaxMs = typeKeyMaxMs;
    }

    // v0.9.0 — one method shows exactly one panel. The old per-button handlers could leave
    // Playback AND Hotkeys visible at once (TabHotkeys was never unchecked by TabPlayback_Click).
    private void SelectTab(int tab)
    {
        // v0.9.48 — Collapsed, not Hidden: a Hidden panel still reserves layout height, so the
        // dialog grew to the SUM of all four tabs and the visible one floated in dead space.
        SerialPanel.Visibility = tab == 0 ? Visibility.Visible : Visibility.Collapsed;
        PlaybackPanel.Visibility = tab == 1 ? Visibility.Visible : Visibility.Collapsed;
        HotkeysPanel.Visibility = tab == 2 ? Visibility.Visible : Visibility.Collapsed;
        RolesPanel.Visibility = tab == 3 ? Visibility.Visible : Visibility.Collapsed;   // v0.9.45
        BehaviorPanel.Visibility = tab == 4 ? Visibility.Visible : Visibility.Collapsed;
        TabSerial.IsChecked = tab == 0;
        TabPlayback.IsChecked = tab == 1;
        TabHotkeys.IsChecked = tab == 2;
        TabRoles.IsChecked = tab == 3;
        TabBehavior.IsChecked = tab == 4;
    }

    /// <summary>v0.9.49 — dock to the owner's right edge at full height instead of floating in the
    /// middle (user request: "attached, not floating"). Falls back to CenterOwner when there is no owner.</summary>
    protected override void OnSourceInitialized(System.EventArgs e)
    {
        base.OnSourceInitialized(e);
        if (Owner is null) return;
        WindowStartupLocation = WindowStartupLocation.Manual;
        SizeToContent = SizeToContent.Manual;
        var wa = SystemParameters.WorkArea;
        double left = Owner.Left + Owner.ActualWidth - Width;
        double top = Owner.Top;
        Left = System.Math.Max(wa.Left, System.Math.Min(left, wa.Right - Width));
        Top = System.Math.Max(wa.Top, System.Math.Min(top, wa.Bottom - 120));
        Height = System.Math.Min(Owner.ActualHeight, wa.Bottom - Top);
    }

    private void TabPlayback_Click(object sender, RoutedEventArgs e) => SelectTab(1);
    private void TabHotkeys_Click(object sender, RoutedEventArgs e) => SelectTab(2);
    private void TabRoles_Click(object sender, RoutedEventArgs e) => SelectTab(3);   // v0.9.45
    private void TabBehavior_Click(object sender, RoutedEventArgs e) => SelectTab(4);
    private void TabSerial_ClickRestore(object sender, RoutedEventArgs e) => SelectTab(0);

    // v0.9.23 — "Measure from my hand": a 20 s in-app capture derives the user's own
    // typing cadence and mouse speed, then fills the boxes (nothing is saved until OK).
    private void Calibrate_Click(object sender, RoutedEventArgs e)
    {
        // v0.9.55 - in embedded mode this Window was never shown, so it cannot be an Owner
        var w = new CalibrationWindow { Owner = _embedded ? System.Windows.Application.Current.MainWindow : this };
        if (w.ShowDialog() == true && w.Result is { } r)
        {
            MouseSpeedMinBox.Text = r.MouseMinPxPerSec.ToString();
            MouseSpeedMaxBox.Text = r.MouseMaxPxPerSec.ToString();
            TypeKeyMinMs = r.KeyMinMs;
            TypeKeyMaxMs = r.KeyMaxMs;
        }
    }

    private void HumanDefaults_Click(object sender, RoutedEventArgs e)
    {
        MouseSpeedMinBox.Text = "300";   // v0.9.24 — recalibrated human default
        MouseSpeedMaxBox.Text = "2000";
    }

    // ── Hotkey auto-capture ────────────────────────────────────────────

    /// <summary>Enter capture mode: highlight the field and wait for key press.</summary>
    private void HotkeyField_Click(object sender, MouseButtonEventArgs e)
    {
        if (_captureInProgess) return;
        var border = (Border)sender;
        _capturingField = border.Tag as string;
        _captureInProgess = true;

        // v0.9.23 — Border is not focusable by default: plain Focus() can return false and
        // keys keep going to whichever control last had focus. Make it focusable first,
        // then take KEYBOARD focus explicitly, and mark the mouse event handled.
        border.Focusable = true;
        Keyboard.Focus(border);
        e.Handled = true;

        // Visual feedback: highlight border
        try {
            border.BorderBrush = (System.Windows.Media.Brush)FindResource("SelectedBorderBrush");
        } catch {
            border.BorderBrush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(100, 150, 255));
        }
        try {
            border.Background = (System.Windows.Media.Brush)FindResource("BgElevatedBrush");
        } catch {
            border.Background = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(30, 50, 80));
        }

        ShowRecordingHint("Press a key, or hold Ctrl/Alt/Shift then press a key…");
    }

    /// <summary>Clear a hotkey field — set to empty string (disabled).</summary>
    private void HotkeyClear_Click(object sender, RoutedEventArgs e)
    {
        if (_captureInProgess) return;
        var btn = (System.Windows.Controls.Button)sender;
        var tag = btn.Tag as string ?? "";
        ClearHotkey(tag);
    }

    /// <summary>Clear and hide a hotkey field by tag name.</summary>
    private void ClearHotkey(string tag)
    {
        switch (tag)
        {
            case "runstopHk":     RunStopHkDisplay.Text = "—";     RunStopHotkey = "";     break;   // v0.9.43 — paired
            case "pauseresumeHk": PauseResumeHkDisplay.Text = "—"; PauseResumeHotkey = ""; break;
        }
    }

    /// <summary>Capture the pressed key combo and display it. Only 2-key combos allowed (1 modifier + 1 key).</summary>
    private void Window_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (!_captureInProgess || _capturingField is null) return;

        // With Alt held WPF reports Key.System and stores the real key in SystemKey.
        // Saving "Alt+System" made an otherwise valid global shortcut impossible to register.
        var pressedKey = e.Key == Key.System ? e.SystemKey : e.Key;

        // Escape — cancel recording
        if (pressedKey == Key.Escape)
        {
            ExitCaptureMode();
            return;
        }

        // ── Modifier pressed first? Remember it and wait for the main key ──
        if (IsModifierKey(pressedKey))
        {
            _activeModifier = GetActiveModifier(e.KeyboardDevice.Modifiers);
            // Visual hint: show which modifier is waiting for the key
            ShowRecordingHint($"Hold {FormatModifiers(_activeModifier)} then press a key…");
            e.Handled = true;
            return;
        }

        // ── Modifier already held + non-modifier key pressed → combo complete ──
        if (_activeModifier != ModifierKeys.None)
        {
            var combo = $"{FormatModifiers(_activeModifier)}+{pressedKey}";
            ApplyHotkey(combo);
            ExitCaptureMode();
            e.Handled = true;
            return;
        }

        // ── No modifier: single-key hotkey allowed only for non-interfering keys ──
        if (!IsSafeAsSingleKey(pressedKey))
        {
            ShowRecordingHint(
                "Single-key: use F1–F24, numpad or navigation keys — or hold a modifier for any key");
            e.Handled = true;
            return;
        }
        ApplyHotkey(pressedKey.ToString());
        ExitCaptureMode();
        e.Handled = true;
    }

    /// <summary>Keys that are safe to bind as single hotkeys (no modifier needed) — e.g.
    /// F-keys, numpad, navigation keys. Letters, digits and printable keys are blocked
    /// because they would fire while the user is typing in any other app.</summary>
    private static bool IsSafeAsSingleKey(System.Windows.Input.Key key)
    {
        // F1–F24
        if (key >= System.Windows.Input.Key.F1 && key <= System.Windows.Input.Key.F24) return true;
        // NumPad0–NumPad9
        if (key >= System.Windows.Input.Key.NumPad0 && key <= System.Windows.Input.Key.NumPad9) return true;
        return key switch
        {
            System.Windows.Input.Key.Add                 // numpad +
            or System.Windows.Input.Key.Subtract         // numpad -
            or System.Windows.Input.Key.Multiply         // numpad *
            or System.Windows.Input.Key.Divide           // numpad /
            or System.Windows.Input.Key.Decimal          // numpad .
            or System.Windows.Input.Key.Insert
            or System.Windows.Input.Key.Delete
            or System.Windows.Input.Key.Home
            or System.Windows.Input.Key.End
            or System.Windows.Input.Key.PageUp
            or System.Windows.Input.Key.PageDown
            or System.Windows.Input.Key.PrintScreen
            or System.Windows.Input.Key.Scroll
            or System.Windows.Input.Key.Pause
            or System.Windows.Input.Key.CapsLock
            or System.Windows.Input.Key.Clear
            => true,
            _ => false,
        };
    }

    /// <summary>Check if a key is purely a modifier (don't treat as a captured key).</summary>
    private static bool IsModifierKey(System.Windows.Input.Key key) => key switch
    {
        System.Windows.Input.Key.LeftCtrl or System.Windows.Input.Key.RightCtrl
            or System.Windows.Input.Key.LeftShift or System.Windows.Input.Key.RightShift
            or System.Windows.Input.Key.LeftAlt or System.Windows.Input.Key.RightAlt
            or System.Windows.Input.Key.LWin or System.Windows.Input.Key.RWin
            or System.Windows.Input.Key.Escape => true,
        _ => false,
    };

    /// <summary>Extract the dominant modifier from current state (only one allowed in 2-key combos).</summary>
    private static ModifierKeys GetActiveModifier(ModifierKeys current) =>
        (current & ModifierKeys.Control) != 0 ? ModifierKeys.Control
        : (current & ModifierKeys.Alt)      != 0 ? ModifierKeys.Alt
        : (current & ModifierKeys.Shift)    != 0 ? ModifierKeys.Shift
        : (current & ModifierKeys.Windows)  != 0 ? ModifierKeys.Windows
        : ModifierKeys.None;

    /// <summary>Format modifier flags into a display string.</summary>
    private static string FormatModifiers(ModifierKeys mods) =>
        mods.HasFlag(ModifierKeys.Control) ? "Ctrl"
        : mods.HasFlag(ModifierKeys.Alt)   ? "Alt"
        : mods.HasFlag(ModifierKeys.Shift) ? "Shift"
        : mods.HasFlag(ModifierKeys.Windows) ? "Win"
        : "";

    /// <summary>Apply a validated 2-key combo to the currently capturing field.</summary>
    private void ApplyHotkey(string combo)
    {
        switch (_capturingField)
        {
            case "runstopHk":     RunStopHkDisplay.Text = combo;     RunStopHotkey = combo;     break;   // v0.9.43 — paired
            case "pauseresumeHk": PauseResumeHkDisplay.Text = combo; PauseResumeHotkey = combo; break;
        }
        ShowRecordingHint($"✅ {combo} saved!");
    }

    /// <summary>Show a transient hint message on the hotkeys panel.</summary>
    private void ShowRecordingHint(string message)
    {
        var hint = HotkeysPanel.Children
            .OfType<TextBlock>()
            .FirstOrDefault(t => t.FontSize == 11 && t.TextWrapping == TextWrapping.Wrap);
        if (hint == null) return;
        hint.Text = message;
        try {
            var brush = (System.Windows.Media.Brush)FindResource("TextTertiaryBrush");
            hint.SetValue(System.Windows.Controls.TextBlock.ForegroundProperty, brush);
        } catch { /* ignore */ }
    }

    /// <summary>Exit capture mode — restore visual state.</summary>
    private void ExitCaptureMode()
    {
        _captureInProgess = false;
        _capturingField = null;
        _activeModifier = ModifierKeys.None;

        // Restore all capture borders
        foreach (var b in new[] { RunStopHkCapture, PauseResumeHkCapture })   // v0.9.43 — paired
        {
            try {
                b.BorderBrush = (System.Windows.Media.Brush)FindResource("BorderSubtleBrush");
                b.Background = (System.Windows.Media.Brush)FindResource("BgElevatedBrush");
            } catch { /* ignore */ }
        }

        ShowRecordingHint("Press Escape to cancel recording. Leave blank to disable.");
    }

    // ── Save ───────────────────────────────────────────────────────────

    private void Ok_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(PortBox.Text)) return;
        Port = PortBox.Text.Trim();
        KeyboardBoard = KbdArmRadio.IsChecked == true ? "promicro" : "pico";   // v0.9.44
        NoActivateWhenStopped = NoActivateWhenStoppedBox.IsChecked == true;
        PythonDir = DirBox.Text.Trim();
        ToolkitDir = ToolkitBox.Text.Trim();

        int.TryParse(WordDelayMinBox.Text, out var wmin);
        int.TryParse(WordDelayMaxBox.Text, out var wmax);
        WordDelayMin = Math.Max(0, wmin);
        WordDelayMax = Math.Max(WordDelayMin, wmax);
        UseWordHumanize = WordDelayMax > WordDelayMin;

        int.TryParse(MouseSpeedMinBox.Text, out var msMin);
        int.TryParse(MouseSpeedMaxBox.Text, out var msMax);
        MouseMoveSpeedMin = Math.Max(0, msMin);
        MouseMoveSpeedMax = Math.Max(MouseMoveSpeedMin, msMax);

        // Hotkeys are already stored live in the fields above — just pass them through
        // Duplicate check: ignore empty strings, warn on any real collision
        var active = new List<string>();
        if (!string.IsNullOrEmpty(RunStopHotkey)) active.Add(RunStopHotkey);   // v0.9.43 — paired
        if (!string.IsNullOrEmpty(PauseResumeHotkey)) active.Add(PauseResumeHotkey);
        var dup = active.GroupBy(s => s).FirstOrDefault(g => g.Count() > 1);
        if (dup != null)
        {
            System.Windows.MessageBox.Show(
                $"کلید ترکیبی «{dup.Key}» در بیش از یک فیلد تکرار شده است.\nهر کلید فقط باید به یک عمل اختصاص یابد.",
                "تکراری بودن کلید ترکیبی",
                System.Windows.MessageBoxButton.OK,
                System.Windows.MessageBoxImage.Warning);
            return;
        }

        Finish(true);
    }
}
