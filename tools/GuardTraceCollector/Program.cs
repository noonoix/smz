using System.IO.Ports;
using System.Text;

namespace GuardTraceCollector;

internal static class Program
{
    private const int Baud = 115200;
    private const long MaxLogBytes = 1_048_576;
    private const int KeepLogs = 5;

    public static int Main(string[] args)
    {
        var portArg = Value(args, "--port");
        var outputDir = Value(args, "--output") ?? Path.Combine(AppContext.BaseDirectory, "traces");
        var requestHistory = args.Any(a => string.Equals(a, "--history", StringComparison.OrdinalIgnoreCase));

        Directory.CreateDirectory(outputDir);
        using var serial = OpenBoard(portArg);
        if (serial is null) return 2;

        var logPath = Path.Combine(outputDir, $"guard-trace-{DateTime.Now:yyyyMMdd-HHmmss}.log");
        using var writer = new StreamWriter(logPath, false, new UTF8Encoding(false)) { AutoFlush = true };
        Write(writer, $"COLLECTOR|start|port={serial.PortName}|baud={Baud}");
        Console.WriteLine($"Connected to {serial.PortName}. Recording: {logPath}");
        Console.WriteLine("Press Ctrl+C to stop. The collector is passive after connection.");

        Console.CancelKeyPress += (_, e) => { e.Cancel = true; serial.Close(); };
        if (requestHistory)
        {
            Write(writer, "COLLECTOR|request|DEBUGGET");
            serial.Write("DEBUGGET\n");
        }

        try
        {
            while (serial.IsOpen)
            {
                try
                {
                    var line = serial.ReadLine().TrimEnd('\r', '\n');
                    if (line.Length == 0) continue;
                    Write(writer, line);
                    Console.WriteLine(line);
                    if (writer.BaseStream.Length >= MaxLogBytes)
                    {
                        Write(writer, "COLLECTOR|limit|rotating");
                        writer.Flush();
                        break;
                    }
                }
                catch (TimeoutException) { }
            }
        }
        catch (IOException ex) { Write(writer, "COLLECTOR|io-error|" + ex.Message); }
        finally
        {
            Write(writer, "COLLECTOR|stop");
            serial.Close();
            Rotate(outputDir);
        }
        return 0;
    }

    private static SerialPort? OpenBoard(string? requested)
    {
        var ports = requested is not null ? new[] { requested } : SerialPort.GetPortNames().OrderBy(x => x).ToArray();
        if (ports.Length == 0) { Console.Error.WriteLine("No serial ports found."); return null; }
        foreach (var name in ports)
        {
            try
            {
                using var probe = new SerialPort(name, Baud) { NewLine = "\n", ReadTimeout = 150 };
                probe.Open();
                probe.DiscardInBuffer();
                probe.Write("PING\n");
                var deadline = DateTime.UtcNow.AddMilliseconds(1200);
                while (DateTime.UtcNow < deadline)
                {
                    try
                    {
                        var line = probe.ReadLine();
                        if (line.Contains("role=brain", StringComparison.OrdinalIgnoreCase)
                            || line.Contains("combined-pico-guard-executor", StringComparison.OrdinalIgnoreCase)
                            || line.Contains("pico-light", StringComparison.OrdinalIgnoreCase))
                        {
                            probe.Close();
                            var live = new SerialPort(name, Baud) { NewLine = "\n", ReadTimeout = 500 };
                            live.Open();
                            return live;
                        }
                    }
                    catch (TimeoutException) { }
                }
            }
            catch (Exception ex) { Console.WriteLine($"{name}: {ex.Message}"); }
        }
        Console.Error.WriteLine("No Pico brain answered PING. Use --port COMx to select a known Pico CDC port.");
        return null;
    }

    private static void Write(StreamWriter writer, string line)
    {
        writer.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} | {line}");
    }

    private static void Rotate(string directory)
    {
        var files = new DirectoryInfo(directory).GetFiles("guard-trace-*.log")
            .OrderByDescending(f => f.LastWriteTimeUtc).ToArray();
        foreach (var file in files.Skip(KeepLogs)) { try { file.Delete(); } catch { } }
    }

    private static string? Value(string[] args, string key)
    {
        var index = Array.FindIndex(args, a => string.Equals(a, key, StringComparison.OrdinalIgnoreCase));
        return index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
    }
}
