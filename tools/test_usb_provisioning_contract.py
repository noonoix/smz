from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "ams-shell/src/Ams.UI/Services/UsbApplicationUpdateService.cs").read_text(encoding="utf-8")
hex_service = (ROOT / "ams-shell/src/Ams.UI/Services/HexInspector.cs").read_text(encoding="utf-8")
prep = (ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml.cs").read_text(encoding="utf-8")
xaml = (ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml").read_text(encoding="utf-8")

required = [
    "RequireApplicationOnly",
    "Touch1200Bps",
    '"avr109"',
    '"-D"',
    "WaitForPort",
    "no ISP",
]
for marker in required:
    assert marker in service, marker
for marker in ["ApplicationOnly", "BootloaderOnly", "WithBootloader", "BootStart", "SHA256"]:
    assert marker in hex_service, marker
assert "InitializeUsbUpdatePanel();" in prep
assert prep.count("public bool CheckOnly { get; set; } = true;") == 1
assert prep.count("public bool Erase { get; set; } = false;") == 1
assert " = true; = true;" not in prep
assert 'x:Name="ChkCheckOnly"' in xaml
check_line = next(line for line in xaml.splitlines() if 'x:Name="ChkCheckOnly"' in line)
assert check_line.count('IsChecked="True"') == 1
assert 'x:Name="ChkErase"' in xaml
erase_line = next(line for line in xaml.splitlines() if 'x:Name="ChkErase"' in line)
assert erase_line.count('IsChecked="False"') == 1
print("USB provisioning contract OK")
