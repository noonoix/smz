from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
boards = ROOT / "ams-shell/src/Ams.UI/Services/BoardsTxtService.cs"
prep = ROOT / "ams-shell/src/Ams.UI/Views/BoardPrepWindow.xaml.cs"

b = boards.read_text(encoding="utf-8")
replacements = [
    (
        'string manufacturer = "AMS", bool crossCore = false)',
        'string manufacturer = "AMS", string serial = "AMS-00000000", bool crossCore = false)',
    ),
    (
        '        boardId = Regex.Replace(boardId.ToLowerInvariant(), "[^a-z0-9_]", "");\n        if (boardId.Length == 0) boardId = "ams";',
        '        boardId = Regex.Replace(boardId.ToLowerInvariant(), "[^a-z0-9_]", "");\n        if (boardId.Length == 0) boardId = "ams";\n        serial = BoardHexService.ValidateSerial(serial);',
    ),
    (
        '            boardId + ".build.usb_manufacturer=\\\"" + manufacturer + "\\\"\\n" +\n            boardId + ".build.board=AVR_LEONARDO\\n" +',
        '            boardId + ".build.usb_manufacturer=\\\"" + manufacturer + "\\\"\\n" +\n            boardId + ".build.usb_serial=\\\"" + serial + "\\\"\\n" +\n            boardId + ".build.board=AVR_LEONARDO\\n" +',
    ),
    (
        'public static string InstallSketchbookPackage(string sketchbookPath, string block)',
        'public static string InstallSketchbookPackage(string sketchbookPath, string block, string serial)',
    ),
    (
        '        else\n        {\n            File.WriteAllText(Path.Combine(pkg, "platform.txt"), PlatformFallback);\n        }\n        return pkg;',
        '        else\n        {\n            File.WriteAllText(Path.Combine(pkg, "platform.txt"), PlatformFallback);\n        }\n        DeviceSpecificAvrCoreService.Install(pkg, serial);\n        return pkg;',
    ),
]
for old, new in replacements:
    if new in b:
        continue
    if b.count(old) != 1:
        raise SystemExit(f"BoardsTxtService patch anchor count {b.count(old)}: {old[:80]}")
    b = b.replace(old, new, 1)
boards.write_text(b, encoding="utf-8", newline="\n")

p = prep.read_text(encoding="utf-8")
# Preview must show the exact serial and local core.
old = 'manufacturer: s.Manuf, crossCore: RadioSketchbook.IsChecked == true);'
new = 'manufacturer: s.Manuf, serial: BoardHexService.ValidateSerial(TxtSerial.Text), crossCore: false);'
if new not in p:
    if p.count(old) != 1:
        raise SystemExit(f"preview patch anchor count {p.count(old)}")
    p = p.replace(old, new, 1)

# Install path: one selected device, serial captured on UI thread, same value in board block and private core.
old = '''            bool sketchbook = RadioSketchbook.IsChecked == true;
            if (!sketchbook)
                throw new InvalidOperationException("برای حفظ Serial اختصاصی اپلیکیشن، نصب فقط به‌صورت پکیج خصوصی Sketchbook مجاز است.");
            var block = BoardsTxtService.BuildBoardBlock(boardId: s.BoardId, name: s.BoardName,
                bootVid: s.BootVid, bootPid: s.BootPid, appPid: s.AppPid, product: s.Product,
                manufacturer: s.Manuf, crossCore: sketchbook);'''
new = '''            bool sketchbook = RadioSketchbook.IsChecked == true;
            if (!sketchbook)
                throw new InvalidOperationException("برای حفظ Serial اختصاصی اپلیکیشن، نصب فقط به‌صورت پکیج خصوصی Sketchbook مجاز است.");
            if (!int.TryParse(TxtCount.Text, out var identityCount) || identityCount != 1)
                throw new InvalidOperationException("هر پکیج اپلیکیشن فقط برای یک Serial ساخته می‌شود؛ تعداد را روی ۱ بگذار و برای هر برد جداگانه نصب کن.");
            var serial = BoardHexService.ValidateSerial(TxtSerial.Text);
            var block = BoardsTxtService.BuildBoardBlock(boardId: s.BoardId, name: s.BoardName,
                bootVid: s.BootVid, bootPid: s.BootPid, appPid: s.AppPid, product: s.Product,
                manufacturer: s.Manuf, serial: serial, crossCore: false);'''
if new not in p:
    if p.count(old) != 1:
        raise SystemExit(f"install block patch anchor count {p.count(old)}")
    p = p.replace(old, new, 1)
old = 'var pkg = BoardsTxtService.InstallSketchbookPackage(path, block, BoardHexService.ValidateSerial(TxtSerial.Text));'
new = 'var pkg = BoardsTxtService.InstallSketchbookPackage(path, block, serial);'
if new not in p:
    if p.count(old) != 1:
        raise SystemExit(f"install call patch anchor count {p.count(old)}")
    p = p.replace(old, new, 1)
prep.write_text(p, encoding="utf-8", newline="\n")
print("application USB serial provisioning applied")
