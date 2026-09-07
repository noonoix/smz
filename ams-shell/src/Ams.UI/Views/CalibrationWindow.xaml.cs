using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using Ams.UI.Services;

namespace Ams.UI.Views;

/// <summary>
/// v0.9.23 — "Learn from my hand": a 20-second in-app capture of the user's own typing
/// cadence and mouse motion. Only timestamps and speeds are measured — key identities
/// are never recorded (privacy by construction, unlike a global-hook recorder).
/// </summary>
public partial class CalibrationWindow : Window
{
    private const int DurationMs = 20000;
    private readonly List<long> _keys = new();
    private readonly List<(long Tick, double X, double Y)> _mouse = new();
    private readonly DispatcherTimer _timer;
    private long _startedAt;
    private bool _capturing;

    /// <summary>Set when the user presses Apply after a successful capture.</summary>
    public CalibrationAnalyzer.CalibrationResult? Result { get; private set; }

    public CalibrationWindow()
    {
        InitializeComponent();
        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(50) };
        _timer.Tick += (_, _) =>
        {
            long elapsed = Environment.TickCount64 - _startedAt;
            Progress.Value = Math.Min(DurationMs, elapsed);
            if (elapsed >= DurationMs) StopCapture();
        };
    }

    private void StartStop_Click(object sender, RoutedEventArgs e)
    {
        if (_capturing) { StopCapture(); return; }
        _keys.Clear();
        _mouse.Clear();
        Result = null;
        ApplyBtn.IsEnabled = false;
        _capturing = true;
        _startedAt = Environment.TickCount64;
        StartBtn.Content = "توقف";
        StatusText.Text = "در حال ضبط… در کادر تایپ کن و موس را در ناحیه حرکت بده";
        _timer.Start();
        TypeBox.Focus();
    }

    private void StopCapture()
    {
        _timer.Stop();
        _capturing = false;
        StartBtn.Content = "شروع دوباره";
        var r = CalibrationAnalyzer.Compute(_keys, _mouse);
        if (r is null)
        {
            StatusText.Text = $"نمونه کافی نیست (کلیدها {_keys.Count}، موس {_mouse.Count}) — " +
                              "«شروع دوباره» را بزن و ۲۰ ثانیه‌ی کامل تایپ و حرکت بده";
            return;
        }
        Result = r;
        StatusText.Text =
            $"تایپ: هر {r.KeyMinMs}–{r.KeyMaxMs} ms بین کلیدها (میانه {r.KeyMedianMs:F0}، {r.KeySamples} نمونه)\n" +
            $"موس: {r.MouseMinPxPerSec}–{r.MouseMaxPxPerSec} px/s (میانه {r.MouseMedianPxPerSec:F0}، {r.MouseSamples} نمونه)\n" +
            "برای استفاده به‌عنوان پیش‌فرض انسانی‌ات، «اعمال» را بزن";
        ApplyBtn.IsEnabled = true;
    }

    private void TypeBox_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (!_capturing || e.IsRepeat) return;
        _keys.Add(Environment.TickCount64);   // timestamp only — the key itself is discarded
    }

    private void MouseArea_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
    {
        if (!_capturing) return;
        var p = e.GetPosition(MouseArea);
        _mouse.Add((Environment.TickCount64, p.X, p.Y));
    }

    private void Apply_Click(object sender, RoutedEventArgs e)
    {
        if (Result is null) return;
        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
