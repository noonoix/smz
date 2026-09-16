using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ClassroomStudio.Companion;

internal static class Program
{
    public static async Task Main(string[] args) => await new CompanionServer(args).RunAsync();
}

internal sealed class CompanionServer
{
    private readonly AuditLog _audit = new();
    private readonly UiAutomationHost _ui = new();
    private readonly string? _configuredApp;

    public CompanionServer(string[] args) => _configuredApp = args.Length == 0 ? null : args[0];

    public async Task RunAsync()
    {
        var transport = new StdioMcpTransport(Console.OpenStandardInput(), Console.OpenStandardOutput());
        while (await transport.TryReadAsync() is { } request)
        {
            JsonNode? response;
            try { response = await DispatchAsync(request); }
            catch (Exception ex)
            {
                _audit.Write("request_failed", new { error = ex.GetType().Name, message = ex.Message });
                response = JsonRpc.Error(request.Id, -32000, ex.Message);
            }
            if (response is not null) await transport.WriteAsync(response);
        }
    }

    private async Task<JsonNode?> DispatchAsync(JsonRpcRequest request)
    {
        if (request.Method is "notifications/initialized" or "initialized") return null;
        if (request.Method == "initialize")
            return JsonRpc.Result(request.Id, new { protocolVersion = request.Params?["protocolVersion"]?.GetValue<string>() ?? "2024-11-05", capabilities = new { tools = new { } }, serverInfo = new { name = "classroom-studio-companion", version = "0.1.0" } });
        if (request.Method == "ping") return JsonRpc.Result(request.Id, new { });
        if (request.Method == "tools/list") return JsonRpc.Result(request.Id, new { tools = ToolCatalog.Descriptors });
        if (request.Method != "tools/call") return JsonRpc.Error(request.Id, -32601, "Method not found: " + request.Method);

        var name = request.Params?["name"]?.GetValue<string>() ?? string.Empty;
        var arguments = request.Params?["arguments"] as JsonObject ?? new JsonObject();
        _audit.Write("tool_call", new { tool = name });
        var result = await CallToolAsync(name, arguments);
        return JsonRpc.Result(request.Id, new { content = new[] { new { type = "text", text = JsonSerializer.Serialize(result) } } });
    }

    private async Task<object> CallToolAsync(string name, JsonObject a)
    {
        switch (name)
        {
            case "launch_classroom_studio":
            {
                var process = _ui.LaunchClassroomStudio(a["executable"]?.GetValue<string>() ?? _configuredApp);
                return new { ok = true, pid = process.Id, executable = process.MainModule?.FileName };
            }
            case "list_windows": return new { ok = true, windows = _ui.ListWindows() };
            case "read_status": return new { ok = true, mainWindow = _ui.ReadMainWindowText() };
            case "find_control": return new { ok = true, control = _ui.FindControl(Required(a, "query")) };
            case "click_control":
            {
                var query = Required(a, "query"); DangerousControlPolicy.ThrowIfDenied(query); _ui.ClickControl(query); return new { ok = true, query };
            }
            case "read_visible_text": return new { ok = true, text = _ui.ReadVisibleText(a["query"]?.GetValue<string>()) };
            case "take_screenshot": return new { ok = true, path = _ui.TakeScreenshot(a["path"]?.GetValue<string>()) };
            case "read_application_log":
            {
                var path = a["path"]?.GetValue<string>(); var lines = Math.Clamp(a["tailLines"]?.GetValue<int>() ?? 120, 1, 2000);
                return new { ok = true, path, text = ApplicationLogReader.Read(path, lines) };
            }
            case "export_combined_bundle_to_staging":
            {
                var staging = Path.GetFullPath(a["stagingDirectory"]?.GetValue<string>() ?? Path.Combine(Path.GetTempPath(), "ClassroomStudio-companion", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")));
                Directory.CreateDirectory(staging); var app = _ui.RequireClassroomStudio(); _ui.InvokeCombinedGuardExport(app); _ui.CompleteSaveFileDialog(app, Path.Combine(staging, "plan.txt")); BundleValidator.WaitForBundle(staging, TimeSpan.FromSeconds(15));
                return new { ok = true, stagingDirectory = staging, files = BundleValidator.List(staging) };
            }
            case "list_bundle_files":
            {
                var directory = Path.GetFullPath(Required(a, "stagingDirectory")); return new { ok = true, stagingDirectory = directory, files = BundleValidator.List(directory) };
            }
            case "verify_bundle_manifest":
            {
                var directory = Path.GetFullPath(Required(a, "stagingDirectory")); return new { ok = true, validation = BundleValidator.ValidateBundle(directory) };
            }
            case "verify_sha256_manifest":
            {
                var directory = Path.GetFullPath(Required(a, "stagingDirectory")); return new { ok = true, validation = BundleValidator.ValidateHashes(directory) };
            }
            default: throw new InvalidOperationException("Tool is not allow-listed: " + name);
        }
    }

    private static string Required(JsonObject a, string key) => a[key]?.GetValue<string>() is { Length: > 0 } value ? value : throw new ArgumentException("Missing argument: " + key);
}

internal sealed record JsonRpcRequest(JsonNode? Id, string Method, JsonObject? Params);

internal static class JsonRpc
{
    public static JsonNode Result(JsonNode? id, object result) => new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id?.DeepClone(), ["result"] = JsonSerializer.SerializeToNode(result) };
    public static JsonNode Error(JsonNode? id, int code, string message) => new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id?.DeepClone(), ["error"] = new JsonObject { ["code"] = code, ["message"] = message } };
}

internal sealed class StdioMcpTransport
{
    private readonly Stream _input; private readonly Stream _output;
    public StdioMcpTransport(Stream input, Stream output) { _input = input; _output = output; }

    public async Task<JsonRpcRequest?> TryReadAsync()
    {
        var first = await ReadLineAsync(); if (first is null) return null;
        if (first.StartsWith("Content-Length:", StringComparison.OrdinalIgnoreCase))
        {
            if (!int.TryParse(first[15..].Trim(), out var length) || length < 0 || length > 10_000_000) throw new InvalidDataException("Invalid Content-Length header.");
            while (true) { var header = await ReadLineAsync() ?? throw new EndOfStreamException(); if (header.Length == 0) break; }
            var bytes = new byte[length]; await ReadExactlyAsync(bytes); return Parse(Encoding.UTF8.GetString(bytes));
        }
        return Parse(first);
    }

    public async Task WriteAsync(JsonNode response)
    {
        var bytes = Encoding.UTF8.GetBytes(response.ToJsonString()); var header = Encoding.ASCII.GetBytes($"Content-Length: {bytes.Length}\r\n\r\n");
        await _output.WriteAsync(header); await _output.WriteAsync(bytes); await _output.FlushAsync();
    }

    private async Task<string?> ReadLineAsync()
    {
        var bytes = new List<byte>();
        while (true)
        {
            var b = _input.ReadByte(); if (b < 0) return bytes.Count == 0 ? null : Encoding.UTF8.GetString(bytes.ToArray()).TrimEnd('\r');
            if (b == '\n') return Encoding.UTF8.GetString(bytes.ToArray()).TrimEnd('\r'); bytes.Add((byte)b);
            if (bytes.Count > 1_000_000) throw new InvalidDataException("Input line is too large.");
        }
    }

    private async Task ReadExactlyAsync(byte[] bytes)
    {
        var offset = 0; while (offset < bytes.Length) { var read = await _input.ReadAsync(bytes.AsMemory(offset)); if (read == 0) throw new EndOfStreamException(); offset += read; }
    }

    private static JsonRpcRequest Parse(string json)
    {
        var root = JsonNode.Parse(json)?.AsObject() ?? throw new InvalidDataException("JSON-RPC request must be an object.");
        return new JsonRpcRequest(root["id"]?.DeepClone(), root["method"]?.GetValue<string>() ?? throw new InvalidDataException("JSON-RPC method is missing."), root["params"] as JsonObject);
    }
}
