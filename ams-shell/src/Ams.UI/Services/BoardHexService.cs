// v0.9.50 — Board preparation: faithful C# port of AMS USB Studio's Caterina.hex
// patching (Intel HEX I/O + USB device/string descriptor patching). Golden-tested in
// TestRunner step 50 against the original Python implementation: same inputs produce
// byte-identical output (hashes recorded in docs/board-preparation-v0.9.50.md).
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace Ams.UI.Services;

/// <summary>v0.9.50 — builds Caterina bootloader HEX files with a custom USB identity
/// (VID/PID, unique serial number, product/manufacturer strings) for the Pro Micro arm
/// board. Pure byte logic with no UI, so TestRunner covers it end to end.</summary>
public static class BoardHexService
{
    // ─── HEX structure constants (unchanged from the proven tool) ───
    public const int FlashSize = 0x8000;
    public const int DeviceDescOffset = 0x7EE2;
    public const int StringDescBase = 0x7F00;
    public const int StringDescMax = 0x8000;

    // Windows/Arduino IDE safety contract: every selectable profile uses one neutral
    // CDC identity. Product/manufacturer/serial remain selectable, but third-party
    // VID/PID pairs are never emitted because Windows may bind them to the wrong driver.
    public const int IdeSafeVid = 0x1D50;
    public const int IdeSafeBootPid = 0x615E;
    public const int IdeSafeApplicationPid = 0x615F;
    public const int IdeSafeClass = 0x02;

    /// <summary>Ready-made device profiles. The visible profile names are aliases for
    /// product/manufacturer strings; all emitted USB descriptors use the neutral AMS CDC
    /// identity above so every selection remains a normal Windows serial port.</summary>
    public sealed record DeviceMode(string Key, string Name, int Vid, int Pid,
                                    int ClassType, int Subclass, int Protocol,
                                    string Product, string Manufacturer, bool LabOnly = false);

    // v0.9.54 - list trimmed at the user's request (BBC micro:bit, Calliope mini, Adafruit,
    // ESP32-S2 and Raspberry Pi removed) and every remaining identity carries its real,
    // researched USB strings so selecting a device fills the board-spec form with defaults.
    // v0.9.55 - twenty researched macro-less keyboards remain selectable as aliases;
    // v0.9.69 changes only their emitted USB identity to the shared IDE-safe AMS CDC pair.
    public static readonly DeviceMode[] DeviceModes =
    {
        new("none",      "AMS CDC Serial (پیش‌فرض)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "AMS USB Serial Device", "AMS", false),
        new("stm32",     "STM32 Virtual COM (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "STM32 Virtual COM Port", "STMicroelectronics", false),
        new("xiao",      "Seeed XIAO (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Seeed XIAO (CDC)", "Seeed", false),
        new("microchip", "Microchip CDC Demo (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "CDC RS-232 Emulation Demo", "Microchip", false),
        new("legospike", "LEGO Education SPIKE (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "LEGO Technic Large Hub", "LEGO Education", false),
        new("m5stack",   "M5Stack Core (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "M5Stack Core (CDC)", "M5Stack", false),
        new("g413tklse", "Logitech G413 TKL SE (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "G413 TKL SE Gaming Keyboard", "Logitech", false),
        new("g413se", "Logitech G413 SE (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "G413 SE Gaming Keyboard", "Logitech", false),
        new("gproxtklrapid", "Logitech G PRO X TKL Rapid (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "PRO X TKL RAPID", "Logitech", false),
        new("blackwidowte", "Razer BlackWidow TE (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "BlackWidow Tournament Ed.", "Razer", false),
        new("blackwidowxte", "Razer BlackWidow X TE (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "BlackWidow X Tournament Ed", "Razer", false),
        new("celeritas2", "ZOWIE Celeritas II (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "CELERITAS II", "ZOWIE", false),
        new("mx83tkl", "CHERRY XTRFY MX 8.3 TKL (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "XTRFY MX 8.3 TKL", "CHERRY", false),
        new("alloyorigins", "HyperX Alloy Origins (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "HyperX Alloy Origins", "HyperX", false),
        new("alloyorigins60", "HyperX Alloy Origins 60 (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "HyperX Alloy Origins 60", "HyperX", false),
        new("alloyorigins65", "HyperX Alloy Origins 65 (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "HyperX Alloy Origins 65", "HyperX", false),
        new("duckyone2mini", "Ducky One 2 Mini (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Ducky One 2 Mini", "DuckyChannel", false),
        new("duckyone2promini", "Ducky One 2 Pro Mini (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Ducky One 2 Pro Mini", "DuckyChannel", false),
        new("apexprotkl", "SteelSeries Apex Pro TKL (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Apex Pro TKL", "SteelSeries", false),
        new("apexpromini", "SteelSeries Apex Pro Mini (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Apex Pro Mini", "SteelSeries", false),
        new("keychronk8", "Keychron K8 (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Keychron K8", "Keychron", false),
        new("das5qs2", "Das Keyboard 5QS Mark II (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Das Keyboard 5QS Mark II", "Metadot", false),
        new("zmk650wp", "Zalman ZM-K650-WP (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "ZM-K650-WP", "Zalman", false),
        new("vanguardpro96", "Corsair Vanguard Pro 96 (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "VANGUARD PRO 96", "Corsair", false),
        new("shikarik515", "Fantech Shikari K515 (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "Shikari K515", "Fantech", false),
        new("gomk87rs", "GAMEON KENORA GOMK87-RS (CDC امن)", IdeSafeVid, IdeSafeBootPid, IdeSafeClass, 0x00, 0x00, "KENORA GOMK87-RS", "GAMEON", false),
    };

    public static void EnsureIdeSafeOverride(int vid, int pid)
    {
        if (vid != IdeSafeVid || pid != IdeSafeBootPid)
            throw new ArgumentException($"برای شناسایی قطعی در Windows/Arduino IDE، VID/PID باید {IdeSafeVid:X4}:{IdeSafeBootPid:X4} باشد؛ VID/PID سازنده‌های دیگر قابل استفاده نیست.");
    }

    public static DeviceMode ModeFor(string? key)
        => DeviceModes.FirstOrDefault(m => m.Key == key) ?? DeviceModes[0];

    /// <summary>v0.9.54 - every board-spec field a device needs, so choosing an identity fills
    /// the step-1 advanced boxes and the step-2 board form with that device's real defaults
    /// instead of leaving them blank. The application PID is always the bootloader PID + 1 -
    /// they must differ, the same rule the reference tool printed under its board form.</summary>
    public sealed record BoardDefaults(string BoardId, string BoardName, string BootVid,
                                       string BootPid, string AppPid, string Product, string Manufacturer);

    public static BoardDefaults DefaultsFor(string? key)
    {
        var m = ModeFor(key);
        var id = m.Key is "none" or "generic_cdc" ? "ams" : SanitizeBoardId(m.Key);
        var name = m.Key == "none" ? "Classroom Studio Board" : m.Product;
        return new BoardDefaults(id, name, $"0x{IdeSafeVid:X4}", $"0x{IdeSafeBootPid:X4}",
                                 $"0x{IdeSafeApplicationPid:X4}", m.Product, m.Manufacturer);
    }

    /// <summary>Arduino board ids are lowercase [a-z0-9_]; anything else is dropped.</summary>
    public static string SanitizeBoardId(string? id)
    {
        var clean = Regex.Replace((id ?? "").ToLowerInvariant(), "[^a-z0-9_]", "");
        return clean.Length > 0 ? clean : "ams";
    }

    // ════════════════════════════ Intel HEX I/O ════════════════════════════

    /// <summary>Reads an Intel HEX file into a 32 KB flash image (0xFF-filled).
    /// Throws InvalidDataException on a bad record checksum.</summary>
    public static byte[] ParseHex(string path)
    {
        var flash = new byte[FlashSize];
        Array.Fill(flash, (byte)0xFF);
        int baseAddr = 0;
        foreach (var raw in File.ReadLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line[0] != ':') continue;
            var rec = Convert.FromHexString(line.Substring(1));
            int sum = 0;
            foreach (var b in rec) sum += b;
            if ((sum & 0xFF) != 0)
                throw new InvalidDataException($"Checksum نامعتبر در خط: {line}");
            int count = rec[0], addr = (rec[1] << 8) | rec[2], rtype = rec[3];
            if (rtype == 0x00) Array.Copy(rec, 4, flash, baseAddr + addr, count);
            // Faithful quirk: the original keeps the type-04 base unshifted. A 32 KB image
            // never carries extended-address records, so behaviour is identical either way.
            else if (rtype == 0x04) baseAddr = (rec[4] << 8) | rec[5];
            else if (rtype == 0x01) break;
        }
        return flash;
    }

    /// <summary>Serialises the flash image back to Intel HEX (all-0xFF 16-byte blocks are
    /// dropped; LF line endings — byte-identical to the original tool's output).</summary>
    public static string ToHex(byte[] flash)
    {
        var sb = new StringBuilder();
        for (int addr = 0; addr < FlashSize; addr += 16)
        {
            bool allFF = true;
            for (int i = 0; i < 16; i++)
                if (flash[addr + i] != 0xFF) { allFF = false; break; }
            if (allFF) continue;
            var rec = new StringBuilder(":10").Append(addr.ToString("X4")).Append("00");
            int s = 0x10 + (addr & 0xFF) + ((addr >> 8) & 0xFF);
            for (int i = 0; i < 16; i++)
            {
                rec.Append(flash[addr + i].ToString("X2"));
                s += flash[addr + i];
            }
            int checksum = (256 - (s % 256)) & 0xFF;
            rec.Append(checksum.ToString("X2"));
            sb.Append(rec).Append('\n');
        }
        sb.Append(":00000001FF\n");
        return sb.ToString();
    }

    // ═══════════════════════ Serial & USB descriptors ═══════════════════════

    /// <summary>"prefix-XXXXXXXX" with 8 random upper-hex characters.</summary>
    public static string GenerateRandomSerial(string prefix = "AMS")
    {
        const string HexChars = "0123456789ABCDEF";
        var chars = new char[8];
        for (int i = 0; i < chars.Length; i++) chars[i] = HexChars[Random.Shared.Next(16)];
        return prefix + "-" + new string(chars);
    }

    /// <summary>USB string descriptor: length byte, 0x03, then UTF-16-LE text (max 29 chars).</summary>
    public static byte[] BuildStringDescriptor(string text)
    {
        var encoded = Encoding.Unicode.GetBytes(text);   // UTF-16-LE
        int length = 2 + encoded.Length;
        if (length > 60)
            throw new InvalidDataException($"رشته طولانی است: {text.Length} کاراکتر (حداکثر ۲۹)");
        var desc = new byte[length];
        desc[0] = (byte)length;
        desc[1] = 0x03;
        Array.Copy(encoded, 0, desc, 2, encoded.Length);
        return desc;
    }

    /// <summary>Patches VID/PID and the device class triple at the fixed descriptor offset.</summary>
    public static void PatchDeviceDescriptor(byte[] flash, int vid, int pid,
                                             int classType, int subclass, int protocol)
    {
        flash[DeviceDescOffset + 0x08] = (byte)(vid & 0xFF);
        flash[DeviceDescOffset + 0x09] = (byte)((vid >> 8) & 0xFF);
        flash[DeviceDescOffset + 0x0A] = (byte)(pid & 0xFF);
        flash[DeviceDescOffset + 0x0B] = (byte)((pid >> 8) & 0xFF);
        flash[DeviceDescOffset + 0x04] = (byte)classType;
        flash[DeviceDescOffset + 0x05] = (byte)subclass;
        flash[DeviceDescOffset + 0x06] = (byte)protocol;
    }

    /// <summary>Writes the serial (always) plus optional product/manufacturer string
    /// descriptors into the free region at the top of flash. Faithful to the original:
    /// the product write is skipped silently when its slot is not 0xFF-free, the offset
    /// still advances, and the manufacturer write has no free-space check.</summary>
    public static void PatchStringDescriptors(byte[] flash, string serialText,
                                              string? productName = null, string? manufacturer = null,
                                              int stringOffset = StringDescBase)
    {
        var serialDesc = BuildStringDescriptor(serialText);
        if (stringOffset + serialDesc.Length > StringDescMax)
        {
            bool found = false;
            for (int off = StringDescBase; off < StringDescMax - 60 && !found; off++)
            {
                bool free = true;
                for (int i = 0; i < serialDesc.Length; i++)
                    if (flash[off + i] != 0xFF) { free = false; break; }
                if (free) { stringOffset = off; found = true; }
            }
            if (!found)
                throw new InvalidDataException("فضای خالی برای string descriptor پیدا نشد");
        }
        Array.Copy(serialDesc, 0, flash, stringOffset, serialDesc.Length);

        int nextOffset = stringOffset + serialDesc.Length;

        if (!string.IsNullOrEmpty(productName))
        {
            var productDesc = BuildStringDescriptor(productName);
            bool fits = nextOffset + productDesc.Length <= StringDescMax;
            if (fits)
                for (int i = 0; i < productDesc.Length; i++)
                    if (flash[nextOffset + i] != 0xFF) { fits = false; break; }
            if (fits)
            {
                Array.Copy(productDesc, 0, flash, nextOffset, productDesc.Length);
                flash[DeviceDescOffset + 0x0F] = 1;   // iProduct
            }
            nextOffset += productDesc.Length;
        }

        if (!string.IsNullOrEmpty(manufacturer))
        {
            var manufacturerDesc = BuildStringDescriptor(manufacturer);
            if (nextOffset + manufacturerDesc.Length <= StringDescMax)
            {
                Array.Copy(manufacturerDesc, 0, flash, nextOffset, manufacturerDesc.Length);
                flash[DeviceDescOffset + 0x0E] = 2;   // iManufacturer
            }
        }

        flash[DeviceDescOffset + 0x10] = 0x02;   // iSerial
    }

    /// <summary>Full patch: identity (when both VID and PID are given) + string descriptors.
    /// Never mutates the caller's buffer — returns a patched copy.</summary>
    public static byte[] PatchHex(byte[] flash, string serialText,
                                  int? vid = null, int? pid = null,
                                  int classType = 0x02, int subclass = 0x00, int protocol = 0x00,
                                  string? product = null, string? manufacturer = null)
    {
        var copy = (byte[])flash.Clone();
        if (vid is not null && pid is not null)
            PatchDeviceDescriptor(copy, vid.Value, pid.Value, classType, subclass, protocol);
        PatchStringDescriptors(copy, serialText, product, manufacturer);
        return copy;
    }

    // ═══════════════════════ input validation ═══════════════════════

    private static readonly Regex VidPidRe = new(@"^0[xX][0-9A-Fa-f]{1,4}$", RegexOptions.Compiled);

    public static int ParseVidPid(string? text, string label = "VID")
    {
        text = (text ?? "").Trim();
        if (!VidPidRe.IsMatch(text))
            throw new ArgumentException($"{label} نامعتبر است: «{text}» — قالب درست مثل 0x1D50 است");
        int value = Convert.ToInt32(text.Substring(2), 16);
        if (value <= 0 || value > 0xFFFF)
            throw new ArgumentException($"{label} باید بین 0x0001 تا 0xFFFF باشد");
        return value;
    }

    // v0.9.50 — the original tool's message carried a corrupted character (U+FFFD);
    // this port writes the intended word بنویسید (the project allows zero U+FFFD).
    public static string ValidateSerial(string? serial)
    {
        serial = (serial ?? "").Trim();
        if (serial.Length == 0)
            throw new ArgumentException("سریال خالی است — دکمه 🎲 را بزنید یا دستی بنویسید");
        if (serial.Length > 29)
            throw new ArgumentException($"سریال «{serial}» طولانی است (حداکثر ۲۹ کاراکتر)");
        if (serial.Any(c => c > 127))
            throw new ArgumentException($"سریال «{serial}» باید فقط حروف/اعداد انگلیسی باشد");
        return serial;
    }

    public static string ValidateUsbString(string? text, string label)
    {
        text = (text ?? "").Trim();
        if (text.Length > 0 && text.Any(c => c > 127))
            throw new ArgumentException($"{label} باید فقط حروف/اعداد انگلیسی باشد (توصیه USB)");
        if (text.Length > 29)
            throw new ArgumentException($"{label} طولانی است (حداکثر ۲۹ کاراکتر)");
        return text;
    }
}
