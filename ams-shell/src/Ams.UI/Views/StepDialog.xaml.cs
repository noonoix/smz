using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Ams.UI.Models;

namespace Ams.UI.Views;

/// <summary>
/// Generic modal step dialog. Builds its form from the step type's FieldDefs
/// (design doc §5.5.x dialog maps), validates int fields on OK, and returns the
/// edited values in <see cref="Values"/>.
/// Optional injected tools: a sound Calibrate button (SCAL on the board, §16.6.5)
/// and a full-screen Region Picker button for x/y/w/h field sets (§5.5.12).
/// </summary>
public partial class StepDialog : Window
{
    private readonly IReadOnlyList<FieldDef> _fields;
    private readonly string? _stepType;   // v0.9.24 — resolved from the shared Fields reference

    private readonly Dictionary<string, FrameworkElement> _controls = new();
    private readonly List<(FieldDef Def, System.Windows.Controls.TextBlock? Label, FrameworkElement Control)> _rows = new();
    private readonly Func<Task<int?>>? _calibrate;
    private readonly string? _calibrateTargetKey;
    private readonly Func<Task<(int x, int y, int w, int h)?>>? _pickRegion;

    /// <summary>Edited values when the dialog closes with OK; otherwise null.</summary>
    public Dictionary<string, object?>? Values { get; private set; }

    public StepDialog(string title, IReadOnlyList<FieldDef> fields, IReadOnlyDictionary<string, object?>? current,
                      Func<Task<int?>>? calibrate = null, string? calibrateTargetKey = null,
                      Func<Task<(int x, int y, int w, int h)?>>? pickRegion = null, string? stepType = null)
    {
        InitializeComponent();
        // v0.9.24 — Persian dialog chrome: translate the New:/Edit: prefix; action names stay English
        Title = title.StartsWith("New: ") ? "جدید: " + title[5..]
              : title.StartsWith("Edit: ") ? "ویرایش: " + title[6..]
              : title;
        _fields = fields;
        _stepType = stepType ?? StepDefinitions.FindTypeByFields(fields);   // v0.9.29 — explicit type key: the concatenated fields array never reference-matched a definition, so every per-step override (FaByStep) silently fell back
        _calibrate = calibrate;
        _calibrateTargetKey = calibrateTargetKey;
        _pickRegion = pickRegion;
        BuildForm(current);
        WireConditionalVisibility();   // v0.9.14 — hide fields ruled out by the current mode/toggle
    }

    private void BuildForm(IReadOnlyDictionary<string, object?>? current)
    {
        foreach (var f in _fields)
        {
            object? cur = current is not null && current.TryGetValue(f.Key, out var v) ? v : f.Default;

            System.Windows.Controls.TextBlock? label = null;
            if (f.Kind != FieldKind.Check)
            {
                label = new System.Windows.Controls.TextBlock
                {
                    Text = StepTextsFa.Get(_stepType, f.Key, f.Label),   // v0.9.24 — Persian description
                    TextAlignment = TextAlignment.Right,                    // v0.9.24 — right-aligned RTL
                    Foreground = (System.Windows.Media.Brush)System.Windows.Application.Current.Resources["TextSecondaryBrush"],
                    Margin = new Thickness(0, 8, 0, 4),
                    TextWrapping = TextWrapping.Wrap,
                };
                FormPanel.Children.Add(label);
            }

            FrameworkElement c = f.Kind switch
            {
                FieldKind.Multiline => new Wpf.Ui.Controls.TextBox
                {
                    AcceptsReturn = true, Height = 90,
                    TextWrapping = TextWrapping.Wrap, Text = PropAsString(cur),
                },
                FieldKind.Int => new Wpf.Ui.Controls.TextBox
                {
                    Text = PropAsString(cur),
                    FontFamily = new System.Windows.Media.FontFamily("Cascadia Code"),
                },
                FieldKind.Float => new Wpf.Ui.Controls.TextBox
                {
                    Text = PropAsString(cur),
                    FontFamily = new System.Windows.Media.FontFamily("Cascadia Code"),
                },
                FieldKind.Combo => MakeCombo(f, cur),
                FieldKind.EditableCombo => MakeCombo(f, cur, editable: true),
                FieldKind.AudioDevice => MakeAudioDeviceCombo(cur),   // v0.9.43 — real device names, not an index
                FieldKind.Check => new System.Windows.Controls.CheckBox
                {
                    Content = StepTextsFa.Get(_stepType, f.Key, f.Label),   // v0.9.24 — Persian checkbox text
                    IsChecked = PropAsBool(cur),
                    Margin = new Thickness(0, 8, 0, 0),
                },
                _ => new Wpf.Ui.Controls.TextBox { Text = PropAsString(cur) },
            };

            _controls[f.Key] = c;
            _rows.Add((f, label, c));   // v0.9.14 — tracked for conditional visibility

            // Calibrate button next to the threshold field (§16.6.5)
            if (_calibrate is not null && f.Key == _calibrateTargetKey)
            {
                var btn = new Wpf.Ui.Controls.Button
                {
                    Content = "کالیبره…",
                    Appearance = Wpf.Ui.Controls.ControlAppearance.Secondary,
                    Margin = new Thickness(0, 4, 0, 0),
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Left,
                };
                btn.Click += OnCalibrate;
                FormPanel.Children.Add(c);
                FormPanel.Children.Add(btn);
                continue;
            }

            FormPanel.Children.Add(c);

            // Browse button for path-type fields (playAudio / runExe / openFile) (§5.5.x)
            // Uses a plain WPF Button so it stays visible on the dark panel background.
            if (!string.IsNullOrWhiteSpace(f.BrowseFilter))
            {
                var btn = new System.Windows.Controls.Button
                {
                    Content = "مرور…",
                    Margin = new Thickness(0, 4, 0, 0),
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Left,
                    Padding = new Thickness(8, 2, 8, 2),
                    FontSize = 12,
                    Tag = f.Key,   // store field key for handler
                    Background = (System.Windows.Media.Brush)
                        System.Windows.Application.Current.Resources["AccentBrush"],
                    Foreground = (System.Windows.Media.Brush)
                        System.Windows.Application.Current.Resources["TextPrimaryBrush"],
                };
                btn.Click += OnBrowseClick;
                FormPanel.Children.Add(btn);
            }

            // Region Picker button after the h field of an x/y/w/h set (§5.5.12)
            if (_pickRegion is not null && f.Key == "h"
                && _controls.ContainsKey("x") && _controls.ContainsKey("y") && _controls.ContainsKey("w"))
            {
                var btn = new Wpf.Ui.Controls.Button
                {
                    Content = "انتخاب ناحیه روی صفحه…  (بکش · دابل‌کلیک تأیید می‌کند · Esc لغو)",
                    Appearance = Wpf.Ui.Controls.ControlAppearance.Secondary,
                    Margin = new Thickness(0, 4, 0, 0),
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Left,
                };
                btn.Click += OnPickRegion;
                FormPanel.Children.Add(btn);
            }
        }
    }

    private async void OnCalibrate(object sender, RoutedEventArgs e)
    {
        if (sender is not Wpf.Ui.Controls.Button btn || _calibrate is null || _calibrateTargetKey is null) return;
        btn.IsEnabled = false;
        btn.Content = "در حال نمونه‌برداری از سنسور صدا — سکون…";
        try
        {
            var v = await _calibrate();
            if (v is not null && _controls[_calibrateTargetKey] is Wpf.Ui.Controls.TextBox tb)
                tb.Text = v.Value.ToString();
        }
        finally
        {
            btn.IsEnabled = true;
            btn.Content = "کالیبره…";
        }
    }

    private async void OnPickRegion(object sender, RoutedEventArgs e)
    {
        if (_pickRegion is null) return;
        // Note: we do NOT call Hide()/Show() here. RegionPickerWindow is Topmost and
        // fully opaque, so the StepDialog remains safely behind it. Calling Hide()
        // inside a ShowDialog()-owned modal loop puts WPF into an invalid state and
        // crashes the app on Show() resume.
        var region = await _pickRegion();
        if (region is not null)
        {
            SetIntText("x", region.Value.x);
            SetIntText("y", region.Value.y);
            SetIntText("w", region.Value.w);
            SetIntText("h", region.Value.h);
        }
    }

    private void SetIntText(string key, int value)
    {
        if (_controls.TryGetValue(key, out var c) && c is Wpf.Ui.Controls.TextBox tb)
            tb.Text = value.ToString();
    }

    // v0.9.14 — conditional visibility: fields with HideWhenKey/HideWhenValue collapse while the
    // sibling combo/checkbox currently holds that value (e.g. typeText tuning hides in clipboard
    // mode; Find Image human-move fields hide when the humanMove box is off).
    private void WireConditionalVisibility()
    {
        foreach (var dep in _rows.Where(r => _rows.Any(x => x.Def.HideWhenKey == r.Def.Key)))
        {
            if (dep.Control is System.Windows.Controls.ComboBox combo)
                combo.SelectionChanged += (_, _) => ApplyConditionalVisibility();
            else if (dep.Control is System.Windows.Controls.CheckBox chk)
            {
                chk.Checked += (_, _) => ApplyConditionalVisibility();
                chk.Unchecked += (_, _) => ApplyConditionalVisibility();
            }
        }
        ApplyConditionalVisibility();
    }

    private void ApplyConditionalVisibility()
    {
        foreach (var (def, label, control) in _rows)
        {
            if (def.HideWhenKey is null) continue;
            var dep = _rows.FirstOrDefault(r => r.Def.Key == def.HideWhenKey);
            string? depValue = dep.Control switch
            {
                System.Windows.Controls.ComboBox cb => cb.SelectedItem as string,
                System.Windows.Controls.CheckBox chk => (chk.IsChecked == true).ToString(),
                _ => null,
            };
            // v0.9.29 — HideUnlessValue joins HideWhenValue: forLoop.mode has three laws and a field can be hidden by two
            var vis = StepFieldVisibility.FieldVisible(depValue, def.HideWhenValue, def.HideUnlessValue) ? Visibility.Visible : Visibility.Collapsed;
            control.Visibility = vis;
            if (label is not null) label.Visibility = vis;
        }
    }

    // v0.9.43 — the audio output device is picked by NAME from the devices actually present
    // (user request: a dropdown instead of the numeric "شاخص خروجی صدا"). Tag = the int index.
    private static System.Windows.Controls.ComboBox MakeAudioDeviceCombo(object? cur)
    {
        var cb = new System.Windows.Controls.ComboBox();
        int current = int.TryParse(PropAsString(cur), out var v) ? v : -1;
        cb.Items.Add(new System.Windows.Controls.ComboBoxItem { Content = "خودکار (پیش‌فرض سیستم)", Tag = -1 });
        try
        {
            int n = NAudio.Wave.WaveOut.DeviceCount;
            for (int i = 0; i < n; i++)
                cb.Items.Add(new System.Windows.Controls.ComboBoxItem
                {
                    Content = $"#{i} — {NAudio.Wave.WaveOut.GetCapabilities(i).ProductName}",
                    Tag = i,
                });
        }
        catch { /* no audio device / NAudio failure — the auto entry still works */ }
        foreach (System.Windows.Controls.ComboBoxItem it in cb.Items)
            if ((int)it.Tag! == current) { cb.SelectedItem = it; break; }
        if (cb.SelectedIndex < 0) cb.SelectedIndex = 0;
        return cb;
    }

    private static System.Windows.Controls.ComboBox MakeCombo(FieldDef f, object? cur, bool editable = false)
    {
        var cb = new System.Windows.Controls.ComboBox { IsEditable = editable };
        foreach (var o in f.Options ?? Array.Empty<string>()) cb.Items.Add(o);
        if (editable)
        {
            // keep the current value visible even when it is not among the offered options
            var text = PropAsString(cur);
            if (text.Length > 0 && !cb.Items.Contains(text)) cb.Items.Add(text);
            cb.Text = text;
        }
        else
        {
            cb.SelectedItem = PropAsString(cur);
            if (cb.SelectedIndex < 0 && cb.Items.Count > 0) cb.SelectedIndex = 0;
        }
        return cb;
    }

    private void Ok_Click(object sender, RoutedEventArgs e)
    {
        foreach (var f in _fields)
        {
            if (f.Kind == FieldKind.Int &&
                !int.TryParse(((Wpf.Ui.Controls.TextBox)_controls[f.Key]).Text, out _))
            {
                System.Windows.MessageBox.Show(this, $"'{StepTextsFa.Get(_stepType, f.Key, f.Label)}' باید عدد باشد.",
                    "مقدار نامعتبر", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            if (f.Kind == FieldKind.Float &&
                !double.TryParse(((Wpf.Ui.Controls.TextBox)_controls[f.Key]).Text, out _))
            {
                System.Windows.MessageBox.Show(this, $"'{StepTextsFa.Get(_stepType, f.Key, f.Label)}' باید عدد (می‌تواند اعشاری باشد) باشد.",
                    "مقدار نامعتبر", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
        }

        var vals = new Dictionary<string, object?>();
        foreach (var f in _fields)
        {
            vals[f.Key] = f.Kind switch
            {
                FieldKind.Int => int.Parse(((Wpf.Ui.Controls.TextBox)_controls[f.Key]).Text),
                FieldKind.Check => ((System.Windows.Controls.CheckBox)_controls[f.Key]).IsChecked == true,
                FieldKind.Combo => (string?)((System.Windows.Controls.ComboBox)_controls[f.Key]).SelectedItem ?? "",
                FieldKind.EditableCombo => ((System.Windows.Controls.ComboBox)_controls[f.Key]).Text.Trim(),
                FieldKind.AudioDevice => (int)((System.Windows.Controls.ComboBoxItem)((System.Windows.Controls.ComboBox)_controls[f.Key]).SelectedItem).Tag!,   // v0.9.43
                FieldKind.Float => double.Parse(((Wpf.Ui.Controls.TextBox)_controls[f.Key]).Text),
                _ => ((Wpf.Ui.Controls.TextBox)_controls[f.Key]).Text,
            };
        }
        Values = vals;
        DialogResult = true;
    }

    private static string PropAsString(object? v) => v switch
    {
        null => "",
        string s => s,
        System.Text.Json.JsonElement { ValueKind: System.Text.Json.JsonValueKind.String } je => je.GetString() ?? "",
        System.Text.Json.JsonElement je => je.ToString(),
        _ => v.ToString() ?? "",
    };

    private static bool PropAsBool(object? v) => v switch
    {
        bool b => b,
        string s => bool.TryParse(s, out var b2) && b2,
        System.Text.Json.JsonElement { ValueKind: System.Text.Json.JsonValueKind.True } => true,
        _ => false,
    };

    /// <summary>Opens a file dialog and writes the selected path into the field whose key is on Button.Tag.</summary>
    private void OnBrowseClick(object sender, RoutedEventArgs e)
    {
        if (sender is not System.Windows.Controls.Button btn || btn.Tag is not string key) return;
        if (!_controls.TryGetValue(key, out var ctrl) || ctrl is not Wpf.Ui.Controls.TextBox tb) return;

        var browseDef = _fields.FirstOrDefault(f => f.Key == key);
        var filter = browseDef?.BrowseFilter ?? "All files|*.*";

        var dlg = new Microsoft.Win32.OpenFileDialog { Filter = filter };
        if (dlg.ShowDialog(this) != true) return;
        tb.Text = dlg.FileName;
    }
}
