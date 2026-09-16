using System.Text.Json;

namespace ClassroomStudio.Companion;

internal sealed class AuditLog
{
    private readonly string _path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ClassroomStudio", "companion-audit.jsonl");
    private readonly object _gate = new();
    public void Write(string action, object details)
    {
        try { Directory.CreateDirectory(Path.GetDirectoryName(_path)!); var line = JsonSerializer.Serialize(new { utc = DateTime.UtcNow, action, details }); lock (_gate) File.AppendAllText(_path, line + Environment.NewLine); } catch { }
    }
}

internal static class ApplicationLogReader
{
    public static string Read(string? requestedPath, int tailLines)
    {
        if (!string.IsNullOrWhiteSpace(requestedPath)) { var path = Path.GetFullPath(requestedPath); if (!File.Exists(path)) throw new FileNotFoundException("Application log was not found.", path); return string.Join(Environment.NewLine, File.ReadAllLines(path).TakeLast(tailLines)); }
        return "No explicit application log path was supplied. Use read_visible_text to inspect the Classroom Studio serial log surface.";
    }
}
