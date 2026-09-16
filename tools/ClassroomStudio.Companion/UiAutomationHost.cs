using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Windows.Automation;

namespace ClassroomStudio.Companion;

public sealed class UiAutomationHost
{
    private Process? _process;

    public Process RequireClassroomStudio()
    {
        if (_process is { HasExited: false }) return _process;
        foreach (var process in Process.GetProcessesByName("ClassroomStudio"))
        {
            if (process.MainWindowHandle != IntPtr.Zero) { _process = process; return process; }
            process.Dispose();
        }
        throw new InvalidOperationException("Classroom Studio is not running. Use launch_classroom_studio first.");
    }

    public Process LaunchClassroomStudio(string? configuredPath)
    {
        var existing = TryExisting();
        if (existing is not null) return existing;
        var path = ResolveExecutable(configuredPath);
        var process = Process.Start(new ProcessStartInfo(path) { UseShellExecute = true }) ?? throw new InvalidOperationException("Classroom Studio could not be started.");
        _process = process; WaitForWindow(process, TimeSpan.FromSeconds(15)); return process;
    }

    public object[] ListWindows()
    {
        var result = new List<object>();
        foreach (var process in Process.GetProcesses())
        {
            try
            {
                if (process.MainWindowHandle == IntPtr.Zero || string.IsNullOrWhiteSpace(process.MainWindowTitle)) continue;
                result.Add(new { processId = process.Id, title = process.MainWindowTitle, executable = process.MainModule?.FileName });
            }
            catch { }
            finally { process.Dispose(); }
        }
        return result.ToArray();
    }

    public object ReadMainWindowText()
    {
        var process = RequireClassroomStudio(); var root = WaitForWindow(process, TimeSpan.FromSeconds(5));
        return new { processId = process.Id, title = root.Current.Name, text = ReadText(root, 20000) };
    }

    public object FindControl(string query)
    {
        var root = WaitForWindow(RequireClassroomStudio(), TimeSpan.FromSeconds(5));
        var element = Find(root, query) ?? throw new InvalidOperationException("Control not found: " + query);
        return Describe(element);
    }

    public void ClickControl(string query)
    {
        var root = WaitForWindow(RequireClassroomStudio(), TimeSpan.FromSeconds(5));
        var element = Find(root, query) ?? throw new InvalidOperationException("Control not found: " + query);
        Invoke(element);
    }

    public string ReadVisibleText(string? query)
    {
        var root = WaitForWindow(RequireClassroomStudio(), TimeSpan.FromSeconds(5));
        var subtree = string.IsNullOrWhiteSpace(query) ? root : Find(root, query!) ?? throw new InvalidOperationException("Control not found: " + query);
        return ReadText(subtree, 40000);
    }

    public string TakeScreenshot(string? requestedPath)
    {
        var path = Path.GetFullPath(requestedPath ?? Path.Combine(Path.GetTempPath(), "ClassroomStudio-companion", "screen-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".png"));
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var bitmap = new Bitmap(System.Windows.Forms.Screen.PrimaryScreen!.Bounds.Width, System.Windows.Forms.Screen.PrimaryScreen.Bounds.Height);
        using (var graphics = Graphics.FromImage(bitmap)) graphics.CopyFromScreen(0, 0, 0, 0, bitmap.Size);
        bitmap.Save(path, ImageFormat.Png); return path;
    }

    public void InvokeCombinedGuardExport(Process process)
    {
        var root = WaitForWindow(process, TimeSpan.FromSeconds(5)); AutomationElement? button = null;
        foreach (var query in new[] { "Combined Guard", "ساخت Combined Guard Bundle", "Combined Guard Bundle" }) { button = Find(root, query); if (button is not null) break; }
        if (button is null) throw new InvalidOperationException("Combined Guard export control is not visible.");
        var name = button.Current.Name;
        if (!name.Contains("combined", StringComparison.OrdinalIgnoreCase) || !name.Contains("guard", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Refused to invoke a control that is not the Combined Guard export.");
        Invoke(button);
    }

    public void CompleteSaveFileDialog(Process app, string planPath)
    {
        var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(10);
        while (DateTime.UtcNow < deadline)
        {
            foreach (var dialog in AutomationElement.RootElement.FindAll(TreeScope.Children, Condition.TrueCondition).Cast<AutomationElement>())
            {
                if (dialog.Current.ProcessId != app.Id) continue;
                var edit = dialog.FindFirst(TreeScope.Descendants, new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit));
                var save = dialog.FindFirst(TreeScope.Descendants, new OrCondition(new PropertyCondition(AutomationElement.NameProperty, "Save"), new PropertyCondition(AutomationElement.NameProperty, "ذخیره")));
                if (edit is null || save is null) continue;
                if (edit.TryGetCurrentPattern(ValuePattern.Pattern, out var valuePattern)) ((ValuePattern)valuePattern).SetValue(planPath); else throw new InvalidOperationException("The save dialog filename field is not writable.");
                Invoke(save); return;
            }
            Thread.Sleep(100);
        }
        throw new TimeoutException("Timed out waiting for the Combined Guard save dialog.");
    }

    private static AutomationElement? Find(AutomationElement root, string query)
    {
        var condition = new OrCondition(new PropertyCondition(AutomationElement.NameProperty, query, PropertyConditionFlags.IgnoreCase), new PropertyCondition(AutomationElement.AutomationIdProperty, query, PropertyConditionFlags.IgnoreCase), new PropertyCondition(AutomationElement.ClassNameProperty, query, PropertyConditionFlags.IgnoreCase));
        return root.FindFirst(TreeScope.Descendants, condition);
    }

    private static void Invoke(AutomationElement element)
    {
        if (!element.TryGetCurrentPattern(InvokePattern.Pattern, out var pattern)) throw new InvalidOperationException("Control does not expose a safe Invoke pattern: " + element.Current.Name);
        ((InvokePattern)pattern).Invoke();
    }

    private static object Describe(AutomationElement element) => new { name = element.Current.Name, automationId = element.Current.AutomationId, className = element.Current.ClassName, controlType = element.Current.ControlType.ProgrammaticName, isEnabled = element.Current.IsEnabled, isOffscreen = element.Current.IsOffscreen, processId = element.Current.ProcessId };

    private static string ReadText(AutomationElement root, int max)
    {
        var lines = new List<string>();
        void Add(AutomationElement e)
        {
            if (lines.Sum(x => x.Length) >= max || e.Current.IsOffscreen) return;
            var name = e.Current.Name?.Trim(); if (!string.IsNullOrWhiteSpace(name) && (lines.Count == 0 || !string.Equals(lines[^1], name, StringComparison.Ordinal))) lines.Add(name);
            if (e.TryGetCurrentPattern(ValuePattern.Pattern, out var p)) { var value = ((ValuePattern)p).Current.Value?.Trim(); if (!string.IsNullOrWhiteSpace(value) && !lines.Contains(value, StringComparer.Ordinal)) lines.Add(value); }
            foreach (AutomationElement child in e.FindAll(TreeScope.Children, Condition.TrueCondition)) Add(child);
        }
        Add(root); var text = string.Join(Environment.NewLine, lines); return text.Length > max ? text[..max] : text;
    }

    private static AutomationElement WaitForWindow(Process process, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            try { process.Refresh(); if (process.MainWindowHandle != IntPtr.Zero) return AutomationElement.FromHandle(process.MainWindowHandle); } catch { }
            Thread.Sleep(100);
        }
        throw new TimeoutException("Classroom Studio main window was not available.");
    }

    private Process? TryExisting()
    {
        foreach (var process in Process.GetProcessesByName("ClassroomStudio")) { if (process.MainWindowHandle != IntPtr.Zero) { _process = process; return process; } process.Dispose(); }
        return null;
    }

    private static string ResolveExecutable(string? configuredPath)
    {
        var candidates = new List<string>(); if (!string.IsNullOrWhiteSpace(configuredPath)) candidates.Add(configuredPath);
        candidates.Add(Path.Combine(AppContext.BaseDirectory, "ClassroomStudio.exe")); candidates.Add(Path.Combine(AppContext.BaseDirectory, "..", "ClassroomStudio.exe"));
        var path = candidates.Select(Path.GetFullPath).FirstOrDefault(File.Exists);
        return path ?? throw new FileNotFoundException("ClassroomStudio.exe was not found. Pass its full path to launch_classroom_studio.");
    }
}
