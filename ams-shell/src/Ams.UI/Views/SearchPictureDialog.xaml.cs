using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.UI.Views;

/// <summary>
/// Find Image dialog — mirrors AMK's "Search Picture" dialog (v0.7.7, user request):
/// same field layout + a visible THUMBNAIL of the selected picture. Returns the
/// findImage props through <see cref="Values"/> (same __name/__delay contract as StepDialog).
/// </summary>
public partial class SearchPictureDialog : Window
{
    private readonly ObservableCollection<string> _pictures = new();
    private int _rx, _ry, _rw = 400, _rh = 300;

    public Dictionary<string, object?> Values { get; private set; } = new();

    public SearchPictureDialog(string title, IReadOnlyDictionary<string, object?>? current)
    {
        InitializeComponent();
        Title = title;
        PictureList.ItemsSource = _pictures;

        if (current is not null)
        {
            var loaded = PropEx.GetString(current, "pictures");
            foreach (var p in loaded
                         .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                _pictures.Add(p);
            SimilarityBox.Text = PropEx.GetString(current, "similarity", "75");
            _rx = PropEx.GetInt(current, "x", 0); _ry = PropEx.GetInt(current, "y", 0);
            _rw = PropEx.GetInt(current, "w", 400); _rh = PropEx.GetInt(current, "h", 300);
            NeverBox.IsChecked = PropEx.GetBool(current, "neverTimeout");
            TimeoutValueBox.Text = PropEx.GetInt(current, "timeoutValue", 3).ToString();
            TimeoutUnitCombo.SelectedIndex = PropEx.GetString(current, "timeoutUnit", "second") switch
                { "ms" => 0, "minute" => 2, "hour" => 3, _ => 1 };
            ScopeCombo.SelectedIndex = PropEx.GetString(current, "searchScope", "entireScreen") switch
                { "fromCursor" => 1, "region" => 2, _ => 0 };
            OnFoundCombo.SelectedIndex = PropEx.GetString(current, "onFound", "moveAndClick") switch
                { "moveOnly" => 1, "clickRestoreCursor" => 2, "none" => 3, _ => 0 };
            OnTimeoutCombo.SelectedIndex = PropEx.GetString(current, "onTimeout", "continue") switch
                { "stopWithTip" => 0, "stopSilent" => 1, _ => 2 };
            IfElseBox.IsChecked = PropEx.GetBool(current, "insertIfElse");
            ParkBox.IsChecked = PropEx.GetBool(current, "parkCursor");
            NameBox.Text = PropEx.GetString(current, "__name");
            DelayBox.Text = PropEx.GetInt(current, "__delay", 55).ToString();
            DelayMaxBox.Text = PropEx.GetInt(current, "__delayMax", 0).ToString();   // v0.7.9
        }
        else
        {
            SimilarityBox.Text = "75";
            TimeoutValueBox.Text = "3";
            TimeoutUnitCombo.SelectedIndex = 1;
            ScopeCombo.SelectedIndex = 0;
            OnFoundCombo.SelectedIndex = 0;
            OnTimeoutCombo.SelectedIndex = 2;
            DelayBox.Text = "55";
            DelayMaxBox.Text = "0";   // v0.7.9
        }

        if (_pictures.Count == 0) _pictures.Add("");
        PictureList.SelectedIndex = 0;
        UpdateRegionRow();
        UpdateTimeoutEnabled();
        UpdateIfElseDependency();   // §3.3.1 rule: If-Else checked → timeout action disabled
    }

    // ── picture list / thumbnail ──

    private void PictureList_SelectionChanged(object sender, SelectionChangedEventArgs e) => RefreshPictureUi();

    /// <summary>Preview + Remove-button state. v0.8.1 — also called EXPLICITLY after
    /// Add/Cut/Remove: when the first real picture lands on the placeholder's index (0),
    /// SelectionChanged never fires, so the preview stayed blank and Remove stayed disabled.
    /// v0.8.0 fixed the Count>1 guard; this completes the fix (user report: still broken).</summary>
    private void RefreshPictureUi()
    {
        LoadPreview(PictureList.SelectedItem as string);
        RemoveBtn.IsEnabled = PictureList.SelectedIndex >= 0
            && !string.IsNullOrWhiteSpace(_pictures[PictureList.SelectedIndex]);
    }

    private void LoadPreview(string? path)
    {
        try
        {
            if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
            {
                var bi = new BitmapImage();
                bi.BeginInit();
                bi.CacheOption = BitmapCacheOption.OnLoad;
                bi.UriSource = new Uri(path);
                bi.EndInit();
                bi.Freeze();
                Preview.Source = bi;
                return;
            }
        }
        catch { /* unreadable image → blank preview */ }
        Preview.Source = null;
    }

    private void AddPicture_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Filter = "Pictures|*.bmp;*.png;*.jpg;*.jpeg|All files|*.*",
            Multiselect = true,
        };
        if (dlg.ShowDialog(this) != true) return;
        // Single picture → replace current selection (or first empty slot);
        // multiple pictures → append all (OR-group logic).
        var names = dlg.FileNames.Where(f => !string.IsNullOrWhiteSpace(f)).ToArray();
        if (names.Length == 1)
        {
            int idx = Math.Max(0, PictureList.SelectedIndex);
            if (idx >= _pictures.Count || string.IsNullOrWhiteSpace(_pictures[idx])) _pictures.Clear();
            if (idx >= _pictures.Count) _pictures.Add("");
            _pictures[idx] = names[0];
            PictureList.SelectedIndex = idx;
        }
        else
        {
            if (_pictures.Count == 1 && string.IsNullOrWhiteSpace(_pictures[0])) _pictures.Clear();
            foreach (var f in names) _pictures.Add(f);
            PictureList.SelectedIndex = _pictures.Count - 1;
        }
        RefreshPictureUi();   // v0.8.1
    }

    private void RemovePicture_Click(object sender, RoutedEventArgs e)
    {
        int i = PictureList.SelectedIndex;
        if (i < 0 || i >= _pictures.Count) return;
        _pictures.RemoveAt(i);
        if (_pictures.Count == 0) _pictures.Add("");   // v0.8.0 — the last picture is removable; keep the placeholder row
        PictureList.SelectedIndex = Math.Min(i, _pictures.Count - 1);
        RefreshPictureUi();   // v0.8.1
    }

    private void CommentLink_Click(object sender, RoutedEventArgs e)
        => CommentBox.Visibility = CommentBox.Visibility == Visibility.Visible ? Visibility.Collapsed : Visibility.Visible;

    // ── Cut BMP From Screen / View BMP Position ──

    private void CutBmp_Click(object sender, RoutedEventArgs e)
    {
        var picker = new RegionPickerWindow { Owner = this };
        if (picker.ShowDialog() != true || picker.RegionW <= 0 || picker.RegionH <= 0) return;
        try
        {
            var dir = Path.Combine(AppContext.BaseDirectory, "captures");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, $"cut_{DateTime.Now:yyyyMMdd_HHmmss}.bmp");
            using (var bmp = new System.Drawing.Bitmap(picker.RegionW, picker.RegionH))
            {
                using (var g = System.Drawing.Graphics.FromImage(bmp))
                    g.CopyFromScreen(picker.RegionX, picker.RegionY, 0, 0, bmp.Size);
                bmp.Save(path, System.Drawing.Imaging.ImageFormat.Bmp);
            }
            if (!File.Exists(path)) throw new IOException("capture was not written: " + path);   // v0.8.0 — loud failure instead of a silent "not saved"
            // Cut replaces current selection with the captured region (single image always).
            int cutIdx = Math.Max(0, PictureList.SelectedIndex);
            if (cutIdx >= _pictures.Count || string.IsNullOrWhiteSpace(_pictures[cutIdx])) _pictures.Clear();
            if (cutIdx >= _pictures.Count) _pictures.Add("");
            _pictures[cutIdx] = path;
            PictureList.SelectedIndex = cutIdx;
            RefreshPictureUi();   // v0.8.1 — the cut picture shows immediately (index may stay 0)
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(this, "برش ناموفق: " + ex.Message, Title, MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void ViewPosition_Click(object sender, RoutedEventArgs e)
    {
        var pics = _pictures.Where(p => !string.IsNullOrWhiteSpace(p)).ToList();
        if (pics.Count == 0)
        {
            System.Windows.MessageBox.Show(this, "اول یک تصویر اضافه کن.", Title, MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        int sim = int.TryParse(SimilarityBox.Text, out var s) ? Math.Clamp(s, 1, 100) : 75;
        var (scope, region) = CurrentScope();
        var hit = VisionService.FindOnScreen(pics, sim, scope, region, 1500, false, _ => { }, CancellationToken.None);
        if (!hit.HasValue)
            System.Windows.MessageBox.Show(this, "تصویر هم‌اکنون روی صفحه پیدا نشد.", Title, MessageBoxButton.OK, MessageBoxImage.Information);
        else
            FlashAt(hit.Value);
    }

    private (string scope, System.Drawing.Rectangle? region) CurrentScope()
        => ScopeCombo.SelectedIndex switch
        {
            1 => ("fromCursor", null),
            2 => ("region", new System.Drawing.Rectangle(_rx, _ry, _rw, _rh)),
            _ => ("entireScreen", null),
        };

    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);

    /// <summary>Red flash box at the hit point + move cursor there for ~0.9s (View BMP Position).</summary>
    private void FlashAt(System.Drawing.Point p)
    {
        SetCursorPos(p.X, p.Y);
        var overlay = new Window
        {
            WindowStyle = WindowStyle.None,
            AllowsTransparency = true,
            Background = System.Windows.Media.Brushes.Transparent,
            Topmost = true,
            ShowInTaskbar = false,
            Width = 64,
            Height = 64,
            Left = p.X - 32,
            Top = p.Y - 32,
            Content = new Border
            {
                BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(0xE5, 0x48, 0x4D)),
                BorderThickness = new Thickness(3),
                CornerRadius = new CornerRadius(6),
            },
        };
        overlay.Show();
        var t = new System.Windows.Threading.DispatcherTimer { Interval = TimeSpan.FromMilliseconds(900) };
        t.Tick += (_, _) => { t.Stop(); overlay.Close(); };
        t.Start();
    }

    // ── field dependencies ──

    private void PickRegion_Click(object sender, RoutedEventArgs e)
    {
        var picker = new RegionPickerWindow { Owner = this };
        if (picker.ShowDialog() == true)
        {
            _rx = picker.RegionX; _ry = picker.RegionY; _rw = picker.RegionW; _rh = picker.RegionH;
            UpdateRegionRow();
        }
    }

    private void Scope_Changed(object sender, SelectionChangedEventArgs e) => UpdateRegionRow();
    private void Never_Changed(object sender, RoutedEventArgs e) => UpdateTimeoutEnabled();
    private void IfElse_Changed(object sender, RoutedEventArgs e) => UpdateIfElseDependency();

    private void UpdateRegionRow()
    {
        bool isRegion = ScopeCombo.SelectedIndex == 2;
        RegionRow.Visibility = isRegion ? Visibility.Visible : Visibility.Collapsed;
        RegionText.Text = $"[{_rx},{_ry} {_rw}x{_rh}]";
    }

    private void UpdateTimeoutEnabled()
    {
        bool enabled = NeverBox.IsChecked != true;
        TimeoutValueBox.IsEnabled = enabled;
        TimeoutUnitCombo.IsEnabled = enabled;
    }

    /// <summary>§3.3.1: with "Insert If Else statement" checked, the timeout action is the Else branch's job.</summary>
    private void UpdateIfElseDependency() => OnTimeoutCombo.IsEnabled = IfElseBox.IsChecked != true;

    // ── OK → Values (same contract as StepDialog) ──

    private void Ok_Click(object sender, RoutedEventArgs e)
    {
        var pics = string.Join('\n', _pictures.Where(p => !string.IsNullOrWhiteSpace(p)));
        Values = new Dictionary<string, object?>
        {
            ["pictures"] = pics,
            ["similarity"] = int.TryParse(SimilarityBox.Text, out var s) ? Math.Clamp(s, 1, 100) : 75,
            ["searchScope"] = ScopeCombo.SelectedIndex switch { 1 => "fromCursor", 2 => "region", _ => "entireScreen" },
            ["x"] = _rx, ["y"] = _ry, ["w"] = _rw, ["h"] = _rh,
            ["neverTimeout"] = NeverBox.IsChecked == true,
            ["timeoutValue"] = int.TryParse(TimeoutValueBox.Text, out var t) ? Math.Max(0, t) : 3,
            ["timeoutUnit"] = TimeoutUnitCombo.SelectedIndex switch { 0 => "ms", 2 => "minute", 3 => "hour", _ => "second" },
            ["onFound"] = OnFoundCombo.SelectedIndex switch { 1 => "moveOnly", 2 => "clickRestoreCursor", 3 => "none", _ => "moveAndClick" },
            ["onTimeout"] = OnTimeoutCombo.SelectedIndex switch { 0 => "stopWithTip", 1 => "stopSilent", _ => "continue" },
            ["insertIfElse"] = IfElseBox.IsChecked == true,
            ["parkCursor"] = ParkBox.IsChecked == true,
            ["__name"] = NameBox.Text.Trim(),
            ["__delay"] = int.TryParse(DelayBox.Text, out var d) ? Math.Max(0, d) : 55,
            ["__delayMax"] = int.TryParse(DelayMaxBox.Text, out var dm) ? Math.Max(0, dm) : 0,   // v0.7.9
        };
        if (CommentBox.Visibility == Visibility.Visible && !string.IsNullOrWhiteSpace(CommentBox.Text))
            Values["picComment"] = CommentBox.Text.Trim();
        DialogResult = true;
    }
}
