using System.Security.Cryptography;

namespace Ams.UI.Services;

public enum HexImageKind
{
    Empty,
    ApplicationOnly,
    BootloaderOnly,
    WithBootloader,
}

public sealed record HexInspection(
    string Path,
    int MinAddress,
    int MaxAddress,
    int DataBytes,
    HexImageKind Kind,
    string Sha256)
{
    public string Range => $"0x{MinAddress:X4}-0x{MaxAddress:X4}";
    public bool IsApplicationOnly => Kind == HexImageKind.ApplicationOnly;
}

/// <summary>
/// Intel-HEX inspection used before every board write. It deliberately classifies the
/// payload by address instead of trusting the filename, so an application update can
/// never accidentally receive a bootloader image.
/// </summary>
public static class HexInspector
{
    public const int FlashSize = 0x8000;
    public const int BootStart = 0x7000;

    public static HexInspection Inspect(string path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            throw new FileNotFoundException("فایل HEX پیدا نشد.", path);

        var bytes = new SortedDictionary<int, byte>();
        var extendedBase = 0;
        var lineNumber = 0;
        foreach (var raw in File.ReadLines(path))
        {
            lineNumber++;
            var line = raw.Trim();
            if (line.Length == 0) continue;
            if (!line.StartsWith(':') || (line.Length - 1) % 2 != 0)
                throw new InvalidDataException($"رکورد Intel HEX در خط {lineNumber} نامعتبر است.");

            byte[] record;
            try { record = Convert.FromHexString(line[1..]); }
            catch (FormatException) { throw new InvalidDataException($"رکورد HEX در خط {lineNumber} قابل خواندن نیست."); }
            if (record.Length < 5 || record.Length != record[0] + 5)
                throw new InvalidDataException($"طول رکورد HEX در خط {lineNumber} نامعتبر است.");

            int checksum = 0;
            foreach (var b in record) checksum = (checksum + b) & 0xFF;
            if (checksum != 0)
                throw new InvalidDataException($"Checksum فایل HEX در خط {lineNumber} نامعتبر است.");

            var count = record[0];
            var address = (record[1] << 8) | record[2];
            var type = record[3];
            switch (type)
            {
                case 0x00:
                    var absolute = extendedBase + address;
                    if (absolute < 0 || absolute + count > FlashSize)
                        throw new InvalidDataException($"فایل HEX از محدوده‌ی Flash خارج می‌شود: 0x{absolute:X}.");
                    for (var i = 0; i < count; i++)
                    {
                        var at = absolute + i;
                        var value = record[4 + i];
                        if (bytes.TryGetValue(at, out var old) && old != value)
                            throw new InvalidDataException($"دو رکورد HEX در آدرس 0x{at:X4} با هم تداخل دارند.");
                        bytes[at] = value;
                    }
                    break;
                case 0x01:
                    goto finished;
                case 0x02:
                    if (count != 2) throw new InvalidDataException($"رکورد extended segment در خط {lineNumber} نامعتبر است.");
                    extendedBase = ((record[4] << 8) | record[5]) << 4;
                    break;
                case 0x04:
                    if (count != 2) throw new InvalidDataException($"رکورد extended linear در خط {lineNumber} نامعتبر است.");
                    extendedBase = ((record[4] << 8) | record[5]) << 16;
                    break;
            }
        }

    finished:
        if (bytes.Count == 0) throw new InvalidDataException("فایل HEX هیچ داده‌ای ندارد.");
        var min = bytes.Keys.Min();
        var max = bytes.Keys.Max();
        var kind = min >= BootStart
            ? HexImageKind.BootloaderOnly
            : max < BootStart
                ? HexImageKind.ApplicationOnly
                : HexImageKind.WithBootloader;
        var sha = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
        return new HexInspection(path, min, max, bytes.Count, kind, sha);
    }

    public static HexInspection RequireApplicationOnly(string path)
    {
        var info = Inspect(path);
        if (!info.IsApplicationOnly)
            throw new InvalidDataException(
                $"این فایل برای آپدیت USB مجاز نیست: {info.Kind}، بازه‌ی {info.Range}. " +
                "فقط application-only با انتهای کمتر از 0x7000 پذیرفته می‌شود.");
        return info;
    }

    public static HexInspection RequireBootloaderOnly(string path)
    {
        var info = Inspect(path);
        if (info.Kind != HexImageKind.BootloaderOnly)
            throw new InvalidDataException(
                $"این فایل Bootloader-only نیست: {info.Kind}، بازه‌ی {info.Range}.");
        return info;
    }

    public static string KindText(HexImageKind kind) => kind switch
    {
        HexImageKind.ApplicationOnly => "Application-only",
        HexImageKind.BootloaderOnly => "Bootloader-only",
        HexImageKind.WithBootloader => "With bootloader",
        _ => "Empty",
    };
}
