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
replacements = [
    (
        'manufacturer: s.Manuf, crossCore: RadioSketchbook.IsChecked == true);',
        'manufacturer: s.Manuf, serial: BoardHexService.ValidateSerial(TxtSerial.Text), crossCore: false);',
    ),
    (
        'manufacturer: s.Manuf, crossCore: sketchbook);',
        'manufacturer: s.Manuf, serial: BoardHexService.ValidateSerial(TxtSerial.Text), crossCore: false);',
    ),
    (
        '            bool sketchbook = RadioSketchbook.IsChecked == true;\n            var block = BoardsTxtService.BuildBoardBlock',
        '            bool sketchbook = RadioSketchbook.IsChecked == true;\n            if (!sketchbook)\n                throw new InvalidOperationException("برای حفظ Serial اختصاصی اپلیکیشن، نصب فقط به‌صورت پکیج خصوصی Sketchbook مجاز است.");\n            var block = BoardsTxtService.BuildBoardBlock',
    ),
    (
        'var pkg = BoardsTxtService.InstallSketchbookPackage(path, block);',
        'var pkg = BoardsTxtService.InstallSketchbookPackage(path, block, BoardHexService.ValidateSerial(TxtSerial.Text));',
    ),
]
for old, new in replacements:
    if new in p:
        continue
    if p.count(old) != 1:
        raise SystemExit(f"BoardPrepWindow patch anchor count {p.count(old)}: {old[:80]}")
    p = p.replace(old, new, 1)
prep.write_text(p, encoding="utf-8", newline="\n")
print("application USB serial provisioning applied")
