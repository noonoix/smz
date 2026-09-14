from pathlib import Path
import re

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

# Keep the corrective patch idempotent. Re-running the workflow must normalize
# each attribute to exactly one value, never append a second IsChecked attribute.
x = xaml.read_text(encoding="utf-8")
lines = x.splitlines(keepends=True)
for i, line in enumerate(lines):
    if 'x:Name="ChkCheckOnly"' in line:
        line = re.sub(r'\s+IsChecked="[^"]*"', '', line)
        line = line.replace('Content="فقط چک (بدون نوشتن)"', 'Content="فقط چک (بدون نوشتن)" IsChecked="True"', 1)
        lines[i] = line
    elif 'x:Name="ChkErase"' in line:
        line = re.sub(r'\s+IsChecked="[^"]*"', '', line)
        line = line.replace('Content="پاک‌سازی اول (erase)"', 'Content="پاک‌سازی اول (erase — فقط Recovery)"', 1)
        line = line.replace('Margin="12,0,0,0"', 'Margin="12,0,0,0" IsChecked="False"', 1)
        lines[i] = line
xaml.write_text(''.join(lines), encoding="utf-8", newline="\n")
print("board USB application update path applied")
