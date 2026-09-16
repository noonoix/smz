using System.Text.Json;
using System.Text.Json.Nodes;

namespace ClassroomStudio.Companion;

public static class ToolCatalog
{
    public static readonly JsonArray Descriptors = new()
    {
        Tool("launch_classroom_studio", "Launch or attach to Classroom Studio; software-only.", new { executable = new { type = "string" } }),
        Tool("list_windows", "List visible top-level windows and owning processes.", new { }),
        Tool("read_status", "Read the Classroom Studio main window and visible status text.", new { }),
        Tool("find_control", "Find a visible WPF/UIA control by name, automation id, or class name.", new { query = new { type = "string" } }),
        Tool("click_control", "Invoke a safe software UI control. Hardware, board, run, stop, and guard controls are denied.", new { query = new { type = "string" } }),
        Tool("read_visible_text", "Read visible UI text from the main window or a matching subtree.", new { query = new { type = "string" } }),
        Tool("take_screenshot", "Capture the primary desktop to a local PNG for diagnostics.", new { path = new { type = "string" } }),
        Tool("read_application_log", "Read a local application log or the current visible log surface.", new { path = new { type = "string" }, tailLines = new { type = "integer" } }),
        Tool("export_combined_bundle_to_staging", "Invoke only the software-side Combined Guard export and save it to a clean staging directory.", new { stagingDirectory = new { type = "string" } }),
        Tool("list_bundle_files", "List staged Combined Guard bundle files.", new { stagingDirectory = new { type = "string" } }),
        Tool("verify_bundle_manifest", "Validate required bundle files and manifest/calibration revision parity.", new { stagingDirectory = new { type = "string" } }),
        Tool("verify_sha256_manifest", "Validate SHA256SUMS.txt against staged files.", new { stagingDirectory = new { type = "string" } }),
    };

    public static readonly string[] Names = { "launch_classroom_studio", "list_windows", "read_status", "find_control", "click_control", "read_visible_text", "take_screenshot", "read_application_log", "export_combined_bundle_to_staging", "list_bundle_files", "verify_bundle_manifest", "verify_sha256_manifest" };

    private static JsonObject Tool(string name, string description, object properties)
    {
        var schema = JsonSerializer.SerializeToNode(new { type = "object", properties, additionalProperties = false })!;
        return new JsonObject { ["name"] = name, ["description"] = description, ["inputSchema"] = schema };
    }
}

public static class DangerousControlPolicy
{
    private static readonly string[] DeniedTokens = { "guard on", "guard off", "guard|on", "guard|off", "run", "stop", "connect", "disconnect", "flash", "reset", "halt", "actuator", "serial", "usb", "hid", "pico", "arduino", "promicro", "keyboard", "mouse", "install driver", "copy to circuitpy" };
    public static bool IsDenied(string query) => DeniedTokens.Any(token => query.Contains(token, StringComparison.OrdinalIgnoreCase));
    public static void ThrowIfDenied(string query) { if (IsDenied(query)) throw new InvalidOperationException("Safety policy denied this control query; hardware and execution controls are not exposed."); }
}
