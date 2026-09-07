using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace Ams.UI.Views;

/// <summary>
/// Full-screen region picker overlay (§5.5.12 flow + §5.5.11 cancel keys).
/// Covers the whole virtual screen; coordinates are returned in SCREEN space.
///
/// v0.8.1/v0.8.2 — confirm behavior (on-machine tested, bug-report-cutbmp-region-picker.md):
/// once a valid region exists, ANY left-click confirms immediately (the old double-click
/// path could never fire — the second press's MouseLeftButtonDown reset the region to 0×0
/// before MouseDoubleClick checked it). Enter also confirms. The temporary debug file
/// logging used during diagnosis was removed after the fix was confirmed working.
/// </summary>
public partial class RegionPickerWindow : Window
{
    public int RegionX { get; private set; }
    public int RegionY { get; private set; }
    public int RegionW { get; private set; }
    public int RegionH { get; private set; }

    private readonly int _ox, _oy;          // virtual-screen origin (can be negative)
    private System.Windows.Point _start;
    private double _x, _y, _w, _h;          // current rect in canvas space (normalized)
    private bool _dragging;
    private bool _hasRegion;

    public RegionPickerWindow()
    {
        InitializeComponent();
        Left = SystemParameters.VirtualScreenLeft;
        Top = SystemParameters.VirtualScreenTop;
        Width = SystemParameters.VirtualScreenWidth;
        Height = SystemParameters.VirtualScreenHeight;
        _ox = (int)SystemParameters.VirtualScreenLeft;
        _oy = (int)SystemParameters.VirtualScreenTop;
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        // v0.8.1 — when a valid region already exists, ANY left-click confirms it
        // immediately (no double-click timing/position check — eliminates the ClickCount bug).
        if (_hasRegion && RegionW >= 3 && RegionH >= 3)
        {
            CommitToFields();
            DialogResult = true;
            return;
        }
        // no valid region yet — start a new drag
        _start = e.GetPosition(Canvas);
        _x = _start.X; _y = _start.Y; _w = 0; _h = 0;
        _dragging = true;
        _hasRegion = false;
        CaptureMouse();
        InfoText.Visibility = Visibility.Visible;
        UpdateRect();
    }

    private void Window_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (!_dragging) return;
        var pos = e.GetPosition(Canvas);
        _x = Math.Min(pos.X, _start.X);
        _y = Math.Min(pos.Y, _start.Y);
        _w = Math.Abs(pos.X - _start.X);
        _h = Math.Abs(pos.Y - _start.Y);
        _hasRegion = _w >= 1 && _h >= 1;
        InfoText.Text = $"Rectangle Point 2: ({(int)pos.X + _ox},{(int)pos.Y + _oy})   Size: {(int)_w}x{(int)_h}";
        UpdateRect();
    }

    private void Window_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _dragging = false;
        ReleaseMouseCapture();
        CommitToFields();
        if (_hasRegion)
            HintText.Text = "Click anywhere to confirm the region · Esc / right-click to cancel · Shift+Arrows adjust size";
    }

    private void Window_MouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        // safety net: if LBDN somehow didn't catch it, confirm here too
        CommitToFields();
        if (_hasRegion && RegionW >= 3 && RegionH >= 3)
            DialogResult = true;
    }

    private void Window_MouseRightButtonDown(object sender, MouseButtonEventArgs e)
        => DialogResult = false;   // cancel (§5.5.11)

    private void Window_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { DialogResult = false; return; }
        if (e.Key == Key.Enter && _hasRegion && RegionW >= 3 && RegionH >= 3) { DialogResult = true; return; }   // Enter also confirms
        if (!_hasRegion) return;
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Shift))
        {
            switch (e.Key)   // fine-adjust the box size by 1px (§5.5.11)
            {
                case Key.Right: _w = Math.Max(1, _w + 1); break;
                case Key.Left: _w = Math.Max(1, _w - 1); break;
                case Key.Down: _h = Math.Max(1, _h + 1); break;
                case Key.Up: _h = Math.Max(1, _h - 1); break;
                default: return;
            }
            CommitToFields();
            UpdateRect();
            InfoText.Text = $"Region: [{RegionX},{RegionY} {RegionW}x{RegionH}]";
            e.Handled = true;
        }
    }

    private void CommitToFields()
    {
        // normalize: lowest x/y as origin (§5.5.12 data model)
        RegionX = (int)_x + _ox;
        RegionY = (int)_y + _oy;
        RegionW = Math.Max(1, (int)_w);
        RegionH = Math.Max(1, (int)_h);
    }

    private void UpdateRect()
    {
        Rect.Visibility = Visibility.Visible;
        Canvas.SetLeft(Rect, _x);
        Canvas.SetTop(Rect, _y);
        Rect.Width = _w;
        Rect.Height = _h;

        var mouse = Mouse.GetPosition(Canvas);
        Canvas.SetLeft(InfoText, mouse.X + 14);
        Canvas.SetTop(InfoText, mouse.Y + 14);
    }
}
