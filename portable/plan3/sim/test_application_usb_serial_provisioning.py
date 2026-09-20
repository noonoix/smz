from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
boards = (ROOT / "ams-shell/src/Ams.UI/Services/BoardsTxtService.cs").read_text(encoding="utf-8")
prep = (ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml.cs").read_text(encoding="utf-8")
core = (ROOT / "ams-shell/src/Ams.UI/Services/DeviceSpecificAvrCoreService.cs").read_text(encoding="utf-8")

for marker in (
    "build.usb_serial",
    "DeviceSpecificAvrCoreService.Install(pkg, serial)",
    "InstallSketchbookPackage(string sketchbookPath, string block, string serial)",
):
    assert marker in boards, marker
for marker in (
    "serial: BoardHexService.ValidateSerial(TxtSerial.Text)",
    "crossCore: false",
    "نصب فقط به‌صورت پکیج خصوصی Sketchbook مجاز است",
):
    assert marker in prep, marker
for marker in (
    "AMS_USB_SERIAL_PATCH_V1",
    "STRING_SERIAL[] PROGMEM",
    "USB_SendStringDescriptor(STRING_SERIAL",
    'Path.Combine(packageRoot, "cores", "arduino")',
    'Path.Combine(packageRoot, "variants", "leonardo")',
):
    assert marker in core, marker
assert "File.Copy" in core and "overwrite: true" in core
assert "global Arduino installation is never modified" in core
print("device-specific application USB serial provisioning contract OK")
