from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "ams-shell/src/Ams.UI/Services/UsbApplicationUpdateService.cs").read_text(encoding="utf-8")
hex_service = (ROOT / "ams-shell/src/Ams.UI/Services/HexInspector.cs").read_text(encoding="utf-8")
prep = (ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml.cs").read_text(encoding="utf-8")

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
assert "public bool Erase { get; set; } = false;" in prep
print("USB provisioning contract OK")
