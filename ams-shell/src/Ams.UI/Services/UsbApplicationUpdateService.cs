using System.Diagnostics;
using System.IO.Ports;
using System.Text;

namespace Ams.UI.Services;

public sealed record UsbApplicationUpdateRequest(
    string ApplicationHexPath,
    string RuntimePort,
    int BootVid,
    int BootPid,
    int AppVid,
    int AppPid,
    string AvrDudePath = "avrdude",
    int BootloaderTimeoutSeconds = 12,
    int ApplicationTimeoutSeconds = 12);

public sealed record UsbApplicationUpdateResult(
    bool Success,
    string BootloaderPort,
    string ApplicationPort,
    string UploadCommand,
    string? RuntimeHandshake,
    HexInspection Hex,
    IReadOnlyList<string> Output);

/// <summary>
/// Normal application update path for ATmega32U4/Caterina. It never opens ISP and never
/// sends Chip Erase: 1200-bps touch → Caterina/AVR109 upload → runtime enumeration → checkup.
/// ISP remains a separate recovery-only path in BoardPrepWindow.
/// </summary>
public static class UsbApplicationUpdateService
{
    public static UsbApplicationUpdateResult Update(
        UsbApplicationUpdateRequest request,
        Action<string>? log = null,
        CancellationToken cancellationToken = default)
    {
        var output = new List<string>();
        void Write(string text) { output.Add(text); log?.Invoke(text); }

        var hex = HexInspector.RequireApplicationOnly(request.ApplicationHexPath);
        Write($"HEX: {HexInspector.KindText(hex.Kind)} · {hex.Range} · SHA-256 {hex.Sha256}");
        Write("USB update: no ISP, no Chip Erase, Bootloader محفوظ می‌ماند.");

        var runtime = (request.RuntimePort ?? string.Empty).Trim();
        var runtimePort = runtime.Length == 0 || runtime.Equals("AUTO", StringComparison.OrdinalIgnoreCase)
            ? FindRuntimePort(request)
            : ExtractPort(runtime);
        if (runtimePort.Length == 0)
            throw new InvalidOperationException("پورت Application پیدا نشد. برد را وصل کن یا پورت Runtime را دستی انتخاب کن.");

        Write($"Runtime port: {runtimePort}");
        Touch1200Bps(runtimePort);
        Write("1200-bps touch ارسال شد؛ منتظر پورت Bootloader هستیم…");

        var boot = WaitForPort(request.BootVid, request.BootPid, request.BootloaderTimeoutSeconds,
            cancellationToken);
        if (boot is null)
            throw new TimeoutException($"Bootloader با VID/PID {request.BootVid:X4}:{request.BootPid:X4} در مهلت مقرر ظاهر نشد.");
        Write($"Bootloader: {boot.Device} · {boot.Vid:X4}:{boot.Pid:X4}");

        var command = BuildAvr109Arguments(request, boot.Device);
        Write("Upload protocol: Caterina / AVR109 · -D · بدون erase");
        Write("avrdude " + DisplayArguments(command));
        var exitCode = RunProcess(request.AvrDudePath, command, Write, cancellationToken);
        if (exitCode != 0)
            throw new InvalidOperationException($"آپلود USB شکست خورد (avrdude exit {exitCode}). Bootloader دست‌نخورده باقی مانده است.");

        Write("Upload و Verify توسط avrdude موفق بود؛ منتظر بازگشت Application هستیم…");
        var app = WaitForPort(request.AppVid, request.AppPid, request.ApplicationTimeoutSeconds,
            cancellationToken);
        if (app is null)
            throw new TimeoutException("Application بعد از Upload دوباره Enumerate نشد؛ ISP اجرا نشد و Bootloader حفظ شده است.");

        string? handshake = null;
        try { handshake = BoardCheckupService.Handshake(app.Device); }
        catch (Exception ex) { Write("هشدار: HELLO اجرا نشد: " + ex.Message); }
        if (!string.IsNullOrWhiteSpace(handshake)) Write("AMS handshake: " + handshake);
        else Write("هشدار: Application دیده شد، اما پاسخ HELLO دریافت نشد.");

        Write($"Application: {app.Device} · {app.Vid:X4}:{app.Pid:X4}");
        Write("USB application update کامل شد؛ برای نسخه‌ی بعدی ISP لازم نیست.");
        return new UsbApplicationUpdateResult(true, boot.Device, app.Device,
            "avrdude " + DisplayArguments(command), handshake, hex, output);
    }

    public static void Touch1200Bps(string port)
    {
        try
        {
            using var serial = new SerialPort(port, 1200)
            {
                DtrEnable = true,
                RtsEnable = true,
                ReadTimeout = 250,
                WriteTimeout = 250,
            };
            serial.Open();
            Thread.Sleep(120);
            serial.Close();
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"ورود خودکار به Bootloader از پورت {port} ناموفق بود: {ex.Message}", ex);
        }
    }

    public static List<string> BuildAvr109Arguments(UsbApplicationUpdateRequest request, string bootloaderPort)
        => new()
        {
            "-p", "atmega32u4",
            "-c", "avr109",
            "-P", bootloaderPort,
            "-b", "57600",
            "-D",
            "-U", $"flash:w:{request.ApplicationHexPath}:i",
        };

    public static string DisplayArguments(IEnumerable<string> args)
        => string.Join(" ", args.Select(QuoteIfNeeded));

    private static string QuoteIfNeeded(string value)
        => value.Any(char.IsWhiteSpace) ? "\"" + value.Replace("\"", "\\\"") + "\"" : value;

    private static string ExtractPort(string text)
    {
        var port = text.Split(" — ", StringSplitOptions.None)[0].Split(" - ", StringSplitOptions.None)[0].Trim();
        return port.StartsWith("COM", StringComparison.OrdinalIgnoreCase) ? port : string.Empty;
    }

    private static string FindRuntimePort(UsbApplicationUpdateRequest request)
    {
        var rows = BoardCheckupService.ScanPorts();
        return rows.FirstOrDefault(r => !r.IsPhantom && !r.IsProgrammer && r.Vid == request.AppVid && r.Pid == request.AppPid)?.Device
            ?? rows.FirstOrDefault(r => !r.IsPhantom && !r.IsProgrammer && r.Mode == "اپلیکیشن")?.Device
            ?? string.Empty;
    }

    private static BoardCheckupService.PortInfo? WaitForPort(
        int vid, int pid, int timeoutSeconds, CancellationToken cancellationToken)
    {
        var until = DateTime.UtcNow.AddSeconds(Math.Max(1, timeoutSeconds));
        while (DateTime.UtcNow < until)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                var hit = BoardCheckupService.ScanPorts().FirstOrDefault(r =>
                    !r.IsPhantom && r.Vid == vid && r.Pid == pid);
                if (hit is not null) return hit;
            }
            catch { /* transient PnP/registry changes are normal during re-enumeration */ }
            Thread.Sleep(250);
        }
        return null;
    }

    private static int RunProcess(string fileName, IReadOnlyList<string> args,
        Action<string> log, CancellationToken cancellationToken)
    {
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };
        foreach (var arg in args) psi.ArgumentList.Add(arg);
        using var process = new Process { StartInfo = psi };
        process.Start();
        var stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        process.WaitForExit();
        var text = stdout.GetAwaiter().GetResult();
        if (text.Length > 0) foreach (var line in text.SplitLines()) log(line);
        var error = stderr.GetAwaiter().GetResult();
        if (error.Length > 0) foreach (var line in error.SplitLines()) log("! " + line);
        return process.ExitCode;
    }

    private static IEnumerable<string> SplitLines(this string text)
        => text.Replace("\r\n", "\n").Replace('\r', '\n')
            .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
}
