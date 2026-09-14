using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Ams.UI.Services;

namespace Ams.UI.Views;

public partial class BoardPrepWindow
{
    private TextBox? _usbHexPath;
    private TextBox? _usbRuntimePort;
    private TextBlock? _usbValidation;
    private Button? _usbUpdate;
    private bool _usbUpdateRunning;

    /// <summary>Adds the recurring, safe path to the existing recovery panel without making
    /// the old ISP recovery controls look like a normal application updater.</summary>
    private void InitializeUsbUpdatePanel()
    {
        if (PanelFlash.Content is not StackPanel host) return;

        var card = new Border
        {
            Background = (Brush)FindResource("BgElevatedBrush"),
            BorderBrush = (Brush)FindResource("OkBrush"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(12),
            Margin = new Thickness(0, 0, 0, 12),
        };
        var body = new StackPanel();
        body.Children.Add(new TextBlock
        {
            Text = "فاز ۲ — آپدیت Application فقط با USB",
            FontWeight = FontWeights.SemiBold,
            FontSize = 15,
            Foreground = (Brush)FindResource("OkBrush"),
            TextAlignment = TextAlignment.Right,
        });
        body.Children.Add(new TextBlock
        {
            Text = "برای نسخه‌های روزمره از این مسیر استفاده کن: Build → بررسی App-only → 1200-bps touch → Caterina/AVR109 → Checkup. این مسیر نه ISP را باز می‌کند و نه Chip Erase انجام می‌دهد.",
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 6, 0, 10),
            Foreground = (Brush)FindResource("TextSecondaryBrush"),
            TextAlignment = TextAlignment.Right,
        });

        var hexRow = new Grid { Margin = new Thickness(0, 0, 0, 7) };
        hexRow.ColumnDefinitions.Add(new ColumnDefinition());
        hexRow.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _usbHexPath = new TextBox { FlowDirection = FlowDirection.LeftToRight, FontFamily = new FontFamily("Consolas"), FontSize = 12 };
        var browse = new Button { Content = "انتخاب application.hex…", Padding = new Thickness(9, 3, 9, 3), Margin = new Thickness(8, 0, 0, 0) };
        browse.Click += (_, _) =>
        {
            var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "Application HEX|*.hex" };
            if (dlg.ShowDialog(this) == true) { _usbHexPath.Text = dlg.FileName; ValidateUsbHex(); }
        };
        hexRow.Children.Add(_usbHexPath);
        Grid.SetColumn(browse, 1);
        hexRow.Children.Add(browse);
        body.Children.Add(new TextBlock { Text = "فایل application-only HEX:", Margin = new Thickness(0, 0, 0, 3), TextAlignment = TextAlignment.Right });
        body.Children.Add(hexRow);

        var portRow = new Grid { Margin = new Thickness(0, 0, 0, 7) };
        portRow.ColumnDefinitions.Add(new ColumnDefinition());
        portRow.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _usbRuntimePort = new TextBox { Text = "AUTO", FlowDirection = FlowDirection.LeftToRight, FontFamily = new FontFamily("Consolas"), FontSize = 12 };
        var detect = new Button { Content = "تشخیص Runtime", Padding = new Thickness(9, 3, 9, 3), Margin = new Thickness(8, 0, 0, 0) };
        detect.Click += (_, _) =>
        {
            try
            {
                var specs = BoardSpecsFromUi();
                var appVid = BoardHexService.ParseVidPid(specs.BootVid, "Application VID");
                var appPid = BoardHexService.ParseVidPid(specs.AppPid, "Application PID");
                var row = BoardCheckupService.ScanPorts().FirstOrDefault(p => !p.IsPhantom && p.Vid == appVid && p.Pid == appPid);
                _usbRuntimePort.Text = row?.Device ?? "AUTO";
                Log(row is null ? "USB update: Runtime پیدا نشد؛ AUTO باقی ماند." : "USB update: Runtime " + row.Device);
            }
            catch (Exception ex) { Log("USB update: تشخیص Runtime ناموفق: " + ex.Message); }
        };
        portRow.Children.Add(_usbRuntimePort);
        Grid.SetColumn(detect, 1);
        portRow.Children.Add(detect);
        body.Children.Add(new TextBlock { Text = "پورت Application فعلی (AUTO هم مجاز است):", Margin = new Thickness(0, 0, 0, 3), TextAlignment = TextAlignment.Right });
        body.Children.Add(portRow);

        _usbValidation = new TextBlock
        {
            Text = "ابتدا یک application.hex انتخاب کن.",
            TextWrapping = TextWrapping.Wrap,
            Foreground = (Brush)FindResource("TextSecondaryBrush"),
            Margin = new Thickness(0, 2, 0, 8),
            TextAlignment = TextAlignment.Right,
        };
        body.Children.Add(_usbValidation);
        var actions = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var validate = new Button { Content = "✓ اعتبارسنجی App-only", Padding = new Thickness(10, 4, 10, 4) };
        validate.Click += (_, _) => ValidateUsbHex();
        _usbUpdate = new Button
        {
            Content = "⬆ آپدیت USB (بدون ISP)",
            Padding = new Thickness(12, 4, 12, 4),
            Margin = new Thickness(8, 0, 0, 0),
            Background = (Brush)FindResource("AccentBrush"),
            Foreground = Brushes.White,
            BorderThickness = new Thickness(0),
            IsEnabled = false,
        };
        _usbUpdate.Click += UsbUpdate_Click;
        actions.Children.Add(validate);
        actions.Children.Add(_usbUpdate);
        body.Children.Add(actions);
        card.Child = body;
        host.Children.Insert(0, card);
    }

    private void ValidateUsbHex()
    {
        if (_usbValidation is null || _usbHexPath is null) return;
        try
        {
            var info = HexInspector.RequireApplicationOnly(_usbHexPath.Text.Trim());
            _usbValidation.Text = $"✓ Application-only معتبر · بازه {info.Range} · {info.DataBytes:N0} bytes · SHA-256 {info.Sha256}";
            _usbValidation.Foreground = (Brush)FindResource("OkBrush");
            if (_usbUpdate is not null) _usbUpdate.IsEnabled = true;
            Log("USB update validation: App-only OK — " + info.Range);
        }
        catch (Exception ex)
        {
            _usbValidation.Text = "✗ " + ex.Message;
            _usbValidation.Foreground = (Brush)FindResource("WarnBrush");
            if (_usbUpdate is not null) _usbUpdate.IsEnabled = false;
            Log("USB update validation failed: " + ex.Message);
        }
    }

    private async void UsbUpdate_Click(object? sender, RoutedEventArgs e)
    {
        if (_usbUpdateRunning || _usbHexPath is null || _usbRuntimePort is null) return;
        try
        {
            ValidateUsbHex();
            if (_usbUpdate?.IsEnabled != true) return;
            var specs = BoardSpecsFromUi();
            var request = new UsbApplicationUpdateRequest(
                _usbHexPath.Text.Trim(),
                _usbRuntimePort.Text.Trim(),
                BoardHexService.ParseVidPid(specs.BootVid, "Bootloader VID"),
                BoardHexService.ParseVidPid(specs.BootPid, "Bootloader PID"),
                BoardHexService.ParseVidPid(specs.BootVid, "Application VID"),
                BoardHexService.ParseVidPid(specs.AppPid, "Application PID"));

            _usbUpdateRunning = true;
            _usbUpdate.IsEnabled = false;
            Log("── شروع آپدیت USB Application؛ ISP عمداً استفاده نمی‌شود ──");
            var result = await Task.Run(() => UsbApplicationUpdateService.Update(request,
                line => Dispatcher.BeginInvoke(() => Log("  " + line))));
            SetStatus(result.Success ? "آپدیت USB موفق — Bootloader حفظ شد" : "آپدیت USB ناموفق");
            MessageBox.Show(this,
                "Application با USB نصب شد. Bootloader حفظ شد و برای نسخه‌ی بعدی ISP لازم نیست.\n\n" +
                $"Runtime: {result.ApplicationPort}\nHandshake: {result.RuntimeHandshake ?? "پاسخی دریافت نشد"}",
                "USB Application Update", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            Log("✗ USB application update failed: " + ex.Message);
            SetStatus("آپدیت USB ناموفق — Bootloader دست‌نخورده است؛ Recovery فقط در صورت نیاز");
            MessageBox.Show(this, ex.Message, "USB Application Update", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            _usbUpdateRunning = false;
            if (_usbUpdate is not null) _usbUpdate.IsEnabled = _usbHexPath is not null && File.Exists(_usbHexPath.Text.Trim());
        }
    }
}
