// v0.9.50 — Board preparation: faithful C# port of AMS USB Studio's boards.txt logic
// (marker-delimited managed block + no-admin sketchbook package + path detection).
// Golden-tested in TestRunner step 50 — the block text is byte-identical to the
// original Python output (hash recorded in docs/board-preparation-v0.9.50.md).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace Ams.UI.Services;

/// <summary>v0.9.50 — installs the "Classroom Studio" board definition into the Arduino
/// IDE so any sketch built with it carries the custom USB identity. Two targets: the IDE's
/// own boards.txt, or a no-admin sketchbook hardware package (the default).</summary>
public static class BoardsTxtService
{
    // Managed-block markers — safe, repeatable install/remove.
    public const string BoardMarkStart = "### AMS-BOARD-CONFIG-START ###";
    public const string BoardMarkEnd = "### AMS-BOARD-CONFIG-END ###";

    /// <summary>Builds the boards.txt block with two VID/PID pairs (application +
    /// bootloader = application − 1… same convention as the original tool: the bootloader
    /// PID is the app PID's sibling handled by the caller). crossCore references the IDE's
    /// built-in core (used by the sketchbook package). LF line endings on purpose.</summary>
    public static string BuildBoardBlock(string boardId = "ams", string name = "Classroom Studio Board",
                                         string bootVid = "0x1D50", string bootPid = "0x615E",
                                         string appPid = "0x615F", string product = "AMS Macro Studio",
                                         string manufacturer = "AMS", string serial = "AMS-00000000", bool crossCore = false)
    {
        boardId = Regex.Replace(boardId.ToLowerInvariant(), "[^a-z0-9_]", "");
        if (boardId.Length == 0) boardId = "ams";
        serial = BoardHexService.ValidateSerial(serial);
        string core = crossCore ? "arduino:arduino" : "arduino";
        string variant = crossCore ? "arduino:leonardo" : "leonardo";
        return
            "##############################################################\n" +
            BoardMarkStart + "\n" +
            boardId + ".name=" + name + "\n" +
            "\n" +
            boardId + ".vid.0=" + bootVid + "\n" +
            boardId + ".pid.0=" + appPid + "\n" +
            boardId + ".vid.1=" + bootVid + "\n" +
            boardId + ".pid.1=" + bootPid + "\n" +
            boardId + ".upload_port.0.vid=" + bootVid + "\n" +
            boardId + ".upload_port.0.pid=" + bootPid + "\n" +
            boardId + ".upload_port.1.vid=" + bootVid + "\n" +
            boardId + ".upload_port.1.pid=" + appPid + "\n" +
            boardId + ".upload.tool=avrdude\n" +
            boardId + ".upload.protocol=avr109\n" +
            boardId + ".upload.maximum_size=28672\n" +
            boardId + ".upload.maximum_data_size=2560\n" +
            boardId + ".upload.speed=57600\n" +
            boardId + ".upload.disable_flushing=true\n" +
            boardId + ".upload.use_1200bps_touch=true\n" +
            boardId + ".upload.wait_for_upload_port=true\n" +
            "\n" +
            boardId + ".build.mcu=atmega32u4\n" +
            boardId + ".build.f_cpu=16000000L\n" +
            boardId + ".build.vid=" + bootVid + "\n" +
            boardId + ".build.pid=" + appPid + "\n" +
            boardId + ".build.usb_product=\"" + product + "\"\n" +
            boardId + ".build.usb_manufacturer=\"" + manufacturer + "\"\n" +
            boardId + ".build.usb_serial=\"" + serial + "\"\n" +
            boardId + ".build.board=AVR_LEONARDO\n" +
            boardId + ".build.core=" + core + "\n" +
            boardId + ".build.variant=" + variant + "\n" +
            boardId + ".build.extra_flags={build.usb_flags}\n" +
            BoardMarkEnd + "\n" +
            "##############################################################\n";
    }

    /// <summary>Removes the AMS managed block and any older hand-written lines with the
    /// same board-id prefix.</summary>
    public static string RemoveBoardBlock(string text, string boardId = "ams")
    {
        var pattern = new Regex(@"\r?\n?#+\r?\n" + Regex.Escape(BoardMarkStart) +
                                @"\r?\n.*?" + Regex.Escape(BoardMarkEnd) + @"\r?\n#+\r?\n?",
                                RegexOptions.Singleline);
        text = pattern.Replace(text, "\n");
        var manual = new Regex(@"^\s*" + Regex.Escape(boardId) + @"\.[^\n]*\r?\n", RegexOptions.Multiline);
        return manual.Replace(text, "");
    }

    /// <summary>Adds or replaces the managed board block in an existing boards.txt.
    /// Returns the timestamped backup path (null when the file did not exist).</summary>
    public static string? InstallBoardBlock(string boardsTxtPath, string block, string boardId = "ams")
    {
        string text = "";
        string? backup = null;
        if (File.Exists(boardsTxtPath))
        {
            text = File.ReadAllText(boardsTxtPath);
            backup = boardsTxtPath + ".bak-" + DateTime.Now.ToString("yyyyMMdd-HHmmss");
            File.WriteAllText(backup, text);
        }
        text = RemoveBoardBlock(text, boardId);
        File.WriteAllText(boardsTxtPath, text.TrimEnd() + "\n\n" + block);
        return backup;
    }

    /// <summary>Removes the managed board block from boards.txt. True when something was removed.</summary>
    public static bool UninstallBoardBlock(string boardsTxtPath, string boardId = "ams")
    {
        if (!File.Exists(boardsTxtPath)) return false;
        var text = File.ReadAllText(boardsTxtPath);
        var newText = RemoveBoardBlock(text, boardId);
        if (newText == text) return false;
        var backup = boardsTxtPath + ".bak-" + DateTime.Now.ToString("yyyyMMdd-HHmmss");
        File.WriteAllText(backup, text);
        File.WriteAllText(boardsTxtPath, newText);
        return true;
    }

    /// <summary>Replacement platform.txt — only written when the IDE's own platform.txt
    /// cannot be found. The avrdude section comes from the stock Arduino AVR 1.8.x platform.
    /// LF endings on purpose (identical bytes to the original tool).</summary>
    public const string PlatformFallback =
        "name=AMS AVR Boards\n" +
        "version=3.1.0\n" +
        "\n" +
        "# AVR Uploader/Programmers tools (stock Arduino AVR platform)\n" +
        "tools.avrdude.path={runtime.tools.avrdude.path}\n" +
        "tools.avrdude.cmd.path={path}/bin/avrdude\n" +
        "tools.avrdude.config.path={path}/etc/avrdude.conf\n" +
        "\n" +
        "tools.avrdude.upload.params.verbose=-v\n" +
        "tools.avrdude.upload.params.quiet=-q -q\n" +
        "tools.avrdude.upload.verify=\n" +
        "tools.avrdude.upload.params.noverify=-V\n" +
        "tools.avrdude.upload.pattern=\"{cmd.path}\" \"-C{config.path}\" {upload.verbose} {upload.verify} -p{build.mcu} -c{upload.protocol} \"-P{serial.port}\" \"-b{upload.speed}\" -D \"-Uflash:w:{build.path}/{build.project_name}.hex:i\"\n" +
        "\n" +
        "tools.avrdude.program.params.verbose=-v -v\n" +
        "tools.avrdude.program.params.quiet=-q -q\n" +
        "tools.avrdude.program.verify=\n" +
        "tools.avrdude.program.params.noverify=-V\n" +
        "tools.avrdude.program.pattern=\"{cmd.path}\" \"-C{config.path}\" {program.verbose} {program.verify} -p{build.mcu} -c{protocol} {program.extra_params} \"-Uflash:w:{build.path}/{build.project_name}.hex:i\"\n" +
        "\n" +
        "tools.avrdude.erase.params.verbose=-v -v -v -v\n" +
        "tools.avrdude.erase.params.quiet=-q -q\n" +
        "tools.avrdude.erase.pattern=\"{cmd.path}\" \"-C{config.path}\" {erase.verbose} -p{build.mcu} -c{protocol} {program.extra_params} -e -Ulock:w:{bootloader.unlock_bits}:m -Uefuse:w:{bootloader.extended_fuses}:m -Uhfuse:w:{bootloader.high_fuses}:m -Ulfuse:w:{bootloader.low_fuses}:m\n" +
        "\n" +
        "tools.avrdude.bootloader.params.verbose=-v -v -v -v\n" +
        "tools.avrdude.bootloader.params.quiet=-q -q\n" +
        "tools.avrdude.bootloader.pattern=\"{cmd.path}\" \"-C{config.path}\" {bootloader.verbose} -p{build.mcu} -c{protocol} {program.extra_params} \"-Uflash:w:{runtime.platform.path}/bootloaders/{bootloader.file}:i\" -Ulock:w:{bootloader.lock_bits}:m\n";

    /// <summary>The IDE's own platform.txt (next to its boards.txt), when present.</summary>
    public static string? FindStockPlatformTxt()
    {
        foreach (var (p, exists) in DetectBoardsTxtCandidates())
            if (exists)
            {
                var cand = Path.Combine(Path.GetDirectoryName(p)!, "platform.txt");
                if (File.Exists(cand)) return cand;
            }
        return null;
    }

    /// <summary>Installs the board as a standalone sketchbook hardware package (no admin,
    /// survives IDE updates). platform.txt is copied from the IDE when available so the
    /// avrdude upload recipes exist; otherwise the fallback template is written.</summary>
    public static string InstallSketchbookPackage(string sketchbookPath, string block, string serial)
    {
        var pkg = Path.Combine(sketchbookPath, "hardware", "ams", "avr");
        Directory.CreateDirectory(pkg);
        const string header = "# AMS AVR Boards — installed by Classroom Studio\n" +
                              "# این فایل جایگزین کامل است؛ برای تغییر از برنامه استفاده کنید.\n\n";
        File.WriteAllText(Path.Combine(pkg, "boards.txt"), header + block);

        var stock = FindStockPlatformTxt();
        if (stock is not null)
        {
            var outLines = File.ReadLines(stock).Select(ln =>
                ln.StartsWith("name=") ? "name=AMS AVR Boards" :
                ln.StartsWith("version=") ? "version=3.1.0" : ln);
            File.WriteAllText(Path.Combine(pkg, "platform.txt"), string.Join("\n", outLines) + "\n");
        }
        else
        {
            File.WriteAllText(Path.Combine(pkg, "platform.txt"), PlatformFallback);
        }
        DeviceSpecificAvrCoreService.Install(pkg, serial);
        return pkg;
    }

    public static bool UninstallSketchbookPackage(string sketchbookPath)
    {
        var pkg = Path.Combine(sketchbookPath, "hardware", "ams");
        if (!Directory.Exists(pkg)) return false;
        Directory.Delete(pkg, recursive: true);
        return true;
    }

    /// <summary>Finds the boards.txt files present on the system (IDE 1.x and IDE 2.x).
    /// Each entry is (path, existsRightNow); duplicates removed case-insensitively.</summary>
    public static List<(string Path, bool Exists)> DetectBoardsTxtCandidates()
    {
        var candidates = new List<(string, bool)>();
        foreach (var env in new[] { "ProgramFiles(x86)", "ProgramFiles" })
        {
            var baseDir = Environment.GetEnvironmentVariable(env);
            if (string.IsNullOrEmpty(baseDir)) continue;
            var p = Path.Combine(baseDir, "Arduino", "hardware", "arduino", "avr", "boards.txt");
            candidates.Add((p, File.Exists(p)));
        }
        var local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
        if (!string.IsNullOrEmpty(local))
        {
            var pkgRoot = Path.Combine(local, "Arduino15", "packages", "arduino", "hardware", "avr");
            if (Directory.Exists(pkgRoot))
                foreach (var ver in Directory.GetDirectories(pkgRoot).OrderBy(d => d, StringComparer.Ordinal))
                {
                    var f = Path.Combine(ver, "boards.txt");
                    if (File.Exists(f)) candidates.Add((f, true));
                }
        }
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var unique = new List<(string, bool)>();
        foreach (var c in candidates)
            if (seen.Add(c.Item1)) unique.Add(c);
        return unique;
    }

    /// <summary>Finds the sketchbook folder from the IDE's preferences.txt, else the
    /// default Documents\Arduino.</summary>
    public static string DetectSketchbook()
    {
        var local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
        if (!string.IsNullOrEmpty(local))
        {
            var pref = Path.Combine(local, "Arduino15", "preferences.txt");
            if (File.Exists(pref))
            {
                try
                {
                    foreach (var line in File.ReadLines(pref))
                        if (line.StartsWith("sketchbook.path="))
                        {
                            var p = line.Substring("sketchbook.path=".Length).Trim();
                            if (Directory.Exists(p)) return p;
                        }
                }
                catch { /* unreadable preferences — fall through to the default */ }
            }
        }
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "Arduino");
    }
}
