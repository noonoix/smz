from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cs = ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml.cs"
xaml = ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml"

text = cs.read_text(encoding="utf-8")
old = "        InitializeComponent();\n\n        _settingsPath"
new = "        InitializeComponent();\n        InitializeUsbUpdatePanel();\n\n        _settingsPath"
if old in text and "InitializeUsbUpdatePanel();" not in text:
    text = text.replace(old, new, 1)

# ISP is recovery-only now: a fresh window must not silently request a destructive erase.
text = text.replace("public bool CheckOnly { get; set; }", "public bool CheckOnly { get; set; } = true;", 1)
text = text.replace("public bool Erase { get; set; } = true;", "public bool Erase { get; set; } = false;", 1)
cs.write_text(text, encoding="utf-8", newline="\n")

x = xaml.read_text(encoding="utf-8")
x = x.replace('x:Name="ChkCheckOnly" Content="فقط چک (بدون نوشتن)"', 'x:Name="ChkCheckOnly" Content="فقط چک (بدون نوشتن)" IsChecked="True"', 1)
x = x.replace('x:Name="ChkErase" Content="پاک‌سازی اول (erase)" Margin="12,0,0,0" IsChecked="True"', 'x:Name="ChkErase" Content="پاک‌سازی اول (erase — فقط Recovery)" Margin="12,0,0,0" IsChecked="False"', 1)
xaml.write_text(x, encoding="utf-8", newline="\n")
print("board USB application update path applied")
