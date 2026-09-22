using System.IO.Ports;
using System.Text;

namespace GuardHardwareMonitor;

internal static class Program
{
    private const int Baud = 115200;
    private const int PollMs = 100;
    private const int ProbeMs = 1500;
    private static readonly object LogLock = new();

    public static int Main(string[] args)
    {
        var requested = Arg(args, "--port");
        var armPort = Arg(args, "--arm-port");
        var output = Arg(args, "--output") ?? Path.Combine(AppContext.BaseDirectory, "diagnostics");
        var history = Has(args, "--history");
        var seconds = int.TryParse(Arg(args, "--seconds"), out var s) && s > 0 ? s : 0;
        Directory.CreateDirectory(output);
        var logPath = Path.Combine(output, $"guard-hardware-{DateTime.Now:yyyyMMdd-HHmmss}.log");
        using var log = new StreamWriter(logPath, false, new UTF8Encoding(false)) { AutoFlush = true };
        using var stop = new CancellationTokenSource();
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; stop.Cancel(); };
        var started = DateTime.UtcNow;
        Write(log, "MONITOR|START|passive=1|commands=PING" + (history ? ",DEBUGGET" : ""));
        Console.WriteLine("GuardHardwareMonitor");
        Console.WriteLine($"Log: {logPath}");
        Console.WriteLine("Only PING is sent automatically. No Guard/HID command is sent.");
        Console.WriteLine("Press Ctrl+C to stop.");

        var picoTask = Task.Run(() => WatchBoard("PICO", requested, history, log, stop.Token));
        var armTask = armPort is null ? Task.CompletedTask : Task.Run(() => WatchBoard("ARM", armPort, false, log, stop.Token));
        while (!stop.IsCancellationRequested && (seconds == 0 || (DateTime.UtcNow - started).TotalSeconds < seconds))
        {
            Thread.Sleep(250);
        }
        stop.Cancel();
        try { Task.WaitAll(new[] { picoTask, armTask }, 2000); } catch { }
        Write(log, "MONITOR|STOP");
        return 0;
    }

    private static void WatchBoard(string role, string? requested, bool history, StreamWriter log, CancellationToken token)
    {
        SerialPort? port = null;
        var buffer = new StringBuilder();
        var lastPorts = "";
        var lastHeartbeat = DateTime.UtcNow;
        var verified = false;
        try
        {
            while (!token.IsCancellationRequested)
            {
                var ports = string.Join(",", SerialPort.GetPortNames().Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(x => x));
                if (ports != lastPorts)
                {
                    lastPorts = ports;
                    Record(log, $"PORTS|{ports}");
                }
                if (port is null || !port.IsOpen)
                {
                    Dispose(ref port);
                    verified = false;
                    var name = requested ?? PickCandidate(ports.Split(',', StringSplitOptions.RemoveEmptyEntries), role, log, token);
                    if (name is null) { Thread.Sleep(500); continue; }
                    try
                    {
                        port = new SerialPort(name, Baud) { NewLine = "\n", ReadTimeout = 100 };
                        port.Open();
                        port.DiscardInBuffer();
                        Write(log, $"CONNECT|{role}|port={name}|baud={Baud}");
                        Console.WriteLine($"[{role}] connected {name}");
                        if (role == "PICO")
                        {
                            port.Write("PING\n");
                            Record(log, "TX|PICO|PING");
                        }
                        else
                        {
                            // The Pro Micro port is observed only; no command is sent.
                            Write(log, "ARM|observe-only");
                        }
                    }
                    catch (Exception ex)
                    {
                        Write(log, $"OPEN-FAIL|{role}|port={name}|{Clean(ex)}");
                        Dispose(ref port); Thread.Sleep(500); continue;
                    }
                }

                try
                {
                    var data = port.ReadExisting();
                    if (!string.IsNullOrEmpty(data))
                    {
                        buffer.Append(data);
                        while (true)
                        {
                            var index = buffer.ToString().IndexOf('\n');
                            if (index < 0) break;
                            var line = buffer.ToString(0, index).TrimEnd('\r');
                            buffer.Remove(0, index + 1);
                            if (line.Length == 0) continue;
                            Record(log, $"RX|{role}|{line}");
                            if (role == "PICO" && line.Contains("role=brain", StringComparison.OrdinalIgnoreCase))
                            {
                                verified = true;
                                Record(log, "PING|OK|brain");
                                if (history && port.IsOpen)
                                {
                                    port.Write("DEBUGGET\n");
                                    Record(log, "TX|PICO|DEBUGGET");
                                    history = false;
                                }
                            }
                            Classify(log, role, line);
                        }
                    }
                    if ((DateTime.UtcNow - lastHeartbeat).TotalSeconds >= 5)
                    {
                        lastHeartbeat = DateTime.UtcNow;
                        Record(log, $"HEARTBEAT|{role}|open={port.IsOpen}|verified={verified}");
                        if (role == "PICO" && !verified)
                            Record(log, "PING|TIMEOUT|no brain response yet");
                    }
                    Thread.Sleep(PollMs);
                }
                catch (Exception ex) when (IsDisconnect(ex))
                {
                    Write(log, $"DISCONNECT|{role}|port={port.PortName}|{Clean(ex)}");
                    Console.WriteLine($"[{role}] disconnected; waiting...");
                    Dispose(ref port); buffer.Clear(); Thread.Sleep(500);
                }
            }
        }
        finally
        {
            if (port is not null) Write(log, $"CLOSE|{role}|port={port.PortName}");
            Dispose(ref port);
        }
    }

    private static string? PickCandidate(IEnumerable<string> ports, string role, StreamWriter log, CancellationToken token)
    {
        foreach (var name in ports)
        {
            if (token.IsCancellationRequested) return null;
            try
            {
                using var probe = new SerialPort(name, Baud) { NewLine = "\n", ReadTimeout = 100 };
                probe.Open();
                probe.DiscardInBuffer();
                if (role == "ARM") return name;
                probe.Write("PING\n");
                var deadline = DateTime.UtcNow.AddMilliseconds(ProbeMs);
                while (DateTime.UtcNow < deadline && !token.IsCancellationRequested)
                {
                    var text = probe.ReadExisting();
                    if (text.Contains("role=brain", StringComparison.OrdinalIgnoreCase) || text.Contains("combined-pico-guard-executor", StringComparison.OrdinalIgnoreCase))
                    {
                        Write(log, $"PROBE|PICO|port={name}|brain=1");
                        return name;
                    }
                    Thread.Sleep(20);
                }
            }
            catch (Exception ex) { Write(log, $"PROBE-FAIL|{name}|{Clean(ex)}"); }
        }
        return null;
    }

    private static void Classify(StreamWriter log, string role, string line)
    {
        if (!line.Contains("EVT|", StringComparison.OrdinalIgnoreCase)) return;
        var kind = line.Contains("GP4", StringComparison.OrdinalIgnoreCase) ? "GP4" :
                   line.Contains("GP3", StringComparison.OrdinalIgnoreCase) ? "GP3" :
                   line.Contains("FAIL", StringComparison.OrdinalIgnoreCase) ? "FAIL" :
                   line.Contains("ROUTE", StringComparison.OrdinalIgnoreCase) ? "ROUTE" :
                   line.Contains("STATE", StringComparison.OrdinalIgnoreCase) ? "STATE" :
                   line.Contains("CAL", StringComparison.OrdinalIgnoreCase) ? "CAL" :
                   line.Contains("ARM", StringComparison.OrdinalIgnoreCase) ? "ARM" : "OTHER";
        Write(log, $"EVENT|{role}|{kind}");
    }

    private static void Record(StreamWriter log, string text)
    {
        Write(log, text);
        Console.WriteLine(text);
    }

    private static void Write(StreamWriter log, string text)
    {
        lock (LogLock) log.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} | {text}");
    }
    private static string Clean(Exception ex) => (ex.GetType().Name + ":" + ex.Message).Replace('|', '/').Replace('\r', ' ').Replace('\n', ' ');
    private static bool IsDisconnect(Exception ex) => ex is IOException or InvalidOperationException or UnauthorizedAccessException or OperationCanceledException;
    private static void Dispose(ref SerialPort? p) { try { p?.Close(); } catch { } try { p?.Dispose(); } catch { } p = null; }
    private static bool Has(string[] a, string key) => a.Any(x => string.Equals(x, key, StringComparison.OrdinalIgnoreCase));
    private static string? Arg(string[] a, string key) { var i = Array.FindIndex(a, x => string.Equals(x, key, StringComparison.OrdinalIgnoreCase)); return i >= 0 && i + 1 < a.Length ? a[i + 1] : null; }
}
