using System.Text;

namespace Ams.UI.Services;

/// <summary>
/// Creates a private Arduino AVR core inside the Classroom Studio sketchbook package.
/// The stock ATmega32U4 core derives iSerial from PluggableUSB interface names, so it
/// cannot represent the serial provisioned for one physical board. This service copies
/// the stock core/Leonardo variant and patches only the private copy with that serial.
/// The global Arduino installation is never modified.
/// </summary>
public static class DeviceSpecificAvrCoreService
{
    public const string PatchMarker = "AMS_USB_SERIAL_PATCH_V1";

    public static string Install(string packageRoot, string serial)
    {
        serial = BoardHexService.ValidateSerial(serial);
        var platform = BoardsTxtService.FindStockPlatformTxt()
            ?? throw new FileNotFoundException("Arduino AVR platform.txt پیدا نشد؛ ابتدا Arduino AVR Boards را نصب کن.");
        var stockRoot = Path.GetDirectoryName(platform)!;
        var stockCore = Path.Combine(stockRoot, "cores", "arduino");
        var stockVariant = Path.Combine(stockRoot, "variants", "leonardo");
        if (!Directory.Exists(stockCore) || !Directory.Exists(stockVariant))
            throw new DirectoryNotFoundException("Arduino AVR core یا Leonardo variant پیدا نشد.");

        var localCore = Path.Combine(packageRoot, "cores", "arduino");
        var localVariant = Path.Combine(packageRoot, "variants", "leonardo");
        CopyTree(stockCore, localCore);
        CopyTree(stockVariant, localVariant);

        var usbCore = Path.Combine(localCore, "USBCore.cpp");
        PatchUsbSerial(usbCore, serial);
        return usbCore;
    }

    internal static void PatchUsbSerial(string path, string serial)
    {
        serial = BoardHexService.ValidateSerial(serial);
        var text = File.ReadAllText(path);
        if (text.Contains(PatchMarker, StringComparison.Ordinal))
        {
            var expected = $"const u8 STRING_SERIAL[] PROGMEM = \"{serial}\";";
            if (!text.Contains(expected, StringComparison.Ordinal))
                throw new InvalidDataException("Core خصوصی قبلاً با Serial دیگری ساخته شده است.");
            return;
        }

        const string oldDecl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;";
        const string newDecl = "extern const u8 STRING_MANUFACTURER[] PROGMEM;\nextern const u8 STRING_SERIAL[] PROGMEM; // AMS_USB_SERIAL_PATCH_V1\nextern const DeviceDescriptor USB_DeviceDescriptorIAD PROGMEM;";
        const string oldValue = "const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\n\n\n#define DEVICE_CLASS";
        var newValue = $"const u8 STRING_MANUFACTURER[] PROGMEM = USB_MANUFACTURER;\nconst u8 STRING_SERIAL[] PROGMEM = \"{serial}\";\n\n#define DEVICE_CLASS";
        const string oldBranch = "else if (setup.wValueL == ISERIAL) {\n#ifdef PLUGGABLE_USB_ENABLED\n\t\t\tchar name[ISERIAL_MAX_LEN];\n\t\t\tPluggableUSB().getShortName(name);\n\t\t\treturn USB_SendStringDescriptor((uint8_t*)name, strlen(name), 0);\n#endif\n\t\t}";
        var newBranch = $"else if (setup.wValueL == ISERIAL) {{\n\t\t\treturn USB_SendStringDescriptor(STRING_SERIAL, {serial.Length}, TRANSFER_PGM);\n\t\t}}";

        text = ReplaceExactlyOnce(text, oldDecl, newDecl, "USB declaration");
        text = ReplaceExactlyOnce(text, oldValue, newValue, "USB serial value");
        text = ReplaceExactlyOnce(text, oldBranch, newBranch, "iSerial descriptor branch");
        File.WriteAllText(path, text, new UTF8Encoding(false));
    }

    private static string ReplaceExactlyOnce(string text, string oldText, string newText, string label)
    {
        var first = text.IndexOf(oldText, StringComparison.Ordinal);
        if (first < 0 || text.IndexOf(oldText, first + oldText.Length, StringComparison.Ordinal) >= 0)
            throw new InvalidDataException($"نسخه‌ی Arduino AVR Core برای Patch «{label}» پشتیبانی نمی‌شود.");
        return text[..first] + newText + text[(first + oldText.Length)..];
    }

    private static void CopyTree(string source, string destination)
    {
        Directory.CreateDirectory(destination);
        foreach (var file in Directory.GetFiles(source))
            File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), overwrite: true);
        foreach (var directory in Directory.GetDirectories(source))
            CopyTree(directory, Path.Combine(destination, Path.GetFileName(directory)));
    }
}
