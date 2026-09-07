// v0.9.50 — Board preparation: board checkup (port scan with USB identity + firmware
// HELLO handshake) and the bundled-asset locator. Ported from AMS USB Studio; the
// handshake speaks the real firmware-1.6 frame — see docs/board-preparation-v0.9.50.md.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Text;
using System.Text.RegularExpressions;

namespace Ams.UI.Services;

/// <summary>v0.9.50 — read-only board health check: which COM ports exist, which USB
/// identity they carry (custom or stock Arduino), bootloader vs application mode, and
/// whether the firmware answers HELLO. No board state is ever written.</summary>
public static class BoardCheckupService
{
    public const int AmsBaud = 115200;

    /// <summary>(VID, PID) → (identity name, mode). Convention: application PID = bootloader PID + 1.</summary>
    public static readonly IReadOnlyDictionary<(int Vid, int Pid), (string Name, string Mode)> KnownIdentities =
        new Dictionary<(int, int), (string, string)>
        {
            [(0x1D50, 0x615E)] = ("پیش‌فرض AMS", "بوت‌لودر"),
            [(0x1D50, 0x615F)] = ("پیش‌فرض AMS", "اپلیکیشن"),
            [(0x0483, 0x5740)] = ("STM32 Virtual COM", "بوت‌لودر"),
            [(0x0483, 0x5741)] = ("STM32 Virtual COM", "اپلیکیشن"),
            [(0x2886, 0x802F)] = ("Seeed XIAO", "بوت‌لودر"),
            [(0x2886, 0x8030)] = ("Seeed XIAO", "اپلیکیشن"),
            [(0x04D8, 0x000A)] = ("Microchip CDC Demo", "بوت‌لودر"),
            [(0x04D8, 0x000B)] = ("Microchip CDC Demo", "اپلیکیشن"),
            // v0.9.52/54 - classroom identities (bootloader + application pair each)
            [(0x0694, 0x0009)] = ("LEGO Education SPIKE", "بوت‌لودر"),
            [(0x0694, 0x000A)] = ("LEGO Education SPIKE", "اپلیکیشن"),
            [(0x303A, 0x1001)] = ("M5Stack Core", "بوت‌لودر"),
            [(0x303A, 0x1002)] = ("M5Stack Core", "اپلیکیشن"),
            // v0.9.55 - keyboard identities (bootloader + application pair each)
            [(0x046D, 0xC33A)] = ("Logitech G413 TKL SE", "بوت‌لودر"),
            [(0x046D, 0xC33B)] = ("Logitech G413 TKL SE", "اپلیکیشن"),
            [(0x046D, 0xC33C)] = ("Logitech G413 SE", "بوت‌لودر"),
            [(0x046D, 0xC33D)] = ("Logitech G413 SE", "اپلیکیشن"),
            [(0x046D, 0xC35E)] = ("Logitech G PRO X TKL Rapid", "بوت‌لودر"),
            [(0x046D, 0xC35F)] = ("Logitech G PRO X TKL Rapid", "اپلیکیشن"),
            [(0x1532, 0x011C)] = ("Razer BlackWidow TE", "بوت‌لودر"),
            [(0x1532, 0x011D)] = ("Razer BlackWidow TE", "اپلیکیشن"),
            [(0x1532, 0x021B)] = ("Razer BlackWidow X TE", "بوت‌لودر"),
            [(0x1532, 0x021C)] = ("Razer BlackWidow X TE", "اپلیکیشن"),
            [(0x1AF3, 0x0025)] = ("ZOWIE Celeritas II", "بوت‌لودر"),
            [(0x1AF3, 0x0026)] = ("ZOWIE Celeritas II", "اپلیکیشن"),
            [(0x046A, 0x00B1)] = ("CHERRY XTRFY MX 8.3 TKL", "بوت‌لودر"),
            [(0x046A, 0x00B2)] = ("CHERRY XTRFY MX 8.3 TKL", "اپلیکیشن"),
            [(0x0951, 0x16E5)] = ("HyperX Alloy Origins", "بوت‌لودر"),
            [(0x0951, 0x16E6)] = ("HyperX Alloy Origins", "اپلیکیشن"),
            [(0x0951, 0x16E9)] = ("HyperX Alloy Origins 60", "بوت‌لودر"),
            [(0x0951, 0x16EA)] = ("HyperX Alloy Origins 60", "اپلیکیشن"),
            [(0x0951, 0x16EB)] = ("HyperX Alloy Origins 65", "بوت‌لودر"),
            [(0x0951, 0x16EC)] = ("HyperX Alloy Origins 65", "اپلیکیشن"),
            [(0x04D9, 0x0348)] = ("Ducky One 2 Mini", "بوت‌لودر"),
            [(0x04D9, 0x0349)] = ("Ducky One 2 Mini", "اپلیکیشن"),
            [(0x04D9, 0x0356)] = ("Ducky One 2 Pro Mini", "بوت‌لودر"),
            [(0x04D9, 0x0357)] = ("Ducky One 2 Pro Mini", "اپلیکیشن"),
            [(0x1038, 0x1614)] = ("SteelSeries Apex Pro TKL", "بوت‌لودر"),
            [(0x1038, 0x1615)] = ("SteelSeries Apex Pro TKL", "اپلیکیشن"),
            [(0x1038, 0x1646)] = ("SteelSeries Apex Pro Mini", "بوت‌لودر"),
            [(0x1038, 0x1647)] = ("SteelSeries Apex Pro Mini", "اپلیکیشن"),
            [(0x3434, 0x0180)] = ("Keychron K8", "بوت‌لودر"),
            [(0x3434, 0x0181)] = ("Keychron K8", "اپلیکیشن"),
            [(0x24F0, 0x2038)] = ("Das Keyboard 5QS Mark II", "بوت‌لودر"),
            [(0x24F0, 0x2039)] = ("Das Keyboard 5QS Mark II", "اپلیکیشن"),
            [(0x258A, 0x0006)] = ("Zalman ZM-K650-WP", "بوت‌لودر"),
            [(0x258A, 0x0007)] = ("Zalman ZM-K650-WP", "اپلیکیشن"),
            [(0x1B1C, 0x1BC4)] = ("Corsair Vanguard Pro 96", "بوت‌لودر"),
            [(0x1B1C, 0x1BC5)] = ("Corsair Vanguard Pro 96", "اپلیکیشن"),
            [(0x0C45, 0x7A0C)] = ("Fantech Shikari K515", "بوت‌لودر"),
            [(0x0C45, 0x7A0D)] = ("Fantech Shikari K515", "اپلیکیشن"),
            [(0x258A, 0x010C)] = ("GAMEON KENORA GOMK87-RS", "بوت‌لودر"),
            [(0x258A, 0x010D)] = ("GAMEON KENORA GOMK87-RS", "اپلیکیشن"),
            [(0x2341, 0x8036)] = ("Arduino Leonardo", "احتمالاً پروگرمر (ArduinoISP)"),
            [(0x2341, 0x8037)] = ("Arduino Leonardo", "احتمالاً پروگرمر (ArduinoISP)"),
            [(0x2341, 0x0036)] = ("Arduino Leonardo", "حالت بوت‌لودر"),
        };

    /// <summary>(identity name, mode) or (null, null) when unknown.</summary>
    public static (string? Name, string? Mode) ClassifyPort(int vid, int pid)
        => KnownIdentities.TryGetValue((vid, pid), out var v) ? v : (null, null);

    public sealed record PortInfo(string Device, string Description, int Vid, int Pid,
                                  string Serial, string? Identity, string? Mode, bool IsProgrammer,
                                  bool IsPhantom = false, string RegPath = "")
    {
        public string Display => string.IsNullOrEmpty(Description) ? Device : $"{Device} — {Description}";
    }

    private static readonly Regex VidPidKeyRe = new(@"^VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", RegexOptions.Compiled);

    /// <summary>Full port scan with USB details, read from the Windows registry (no admin
    /// needed): HKLM\SYSTEM\CurrentControlSet\Enum\USB provides VID/PID, the instance serial
    /// and the PortName; HKLM\HARDWARE\DEVICEMAP\SERIALCOMM merges plain COM ports that
    /// carry no USB identity (the same fallback the original tool used).</summary>
    public static List<PortInfo> ScanPorts()
    {
        var rows = new List<PortInfo>();
        if (!OperatingSystem.IsWindows()) return rows;
        var live = LiveSerialCommPorts();   // v0.9.51 — the live set first: it drives phantom detection
        try
        {
            using var usb = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Enum\USB");
            if (usb != null)
            {
                foreach (var idName in usb.GetSubKeyNames())
                {
                    var m = VidPidKeyRe.Match(idName);
                    if (!m.Success) continue;
                    int vid = Convert.ToInt32(m.Groups[1].Value, 16);
                    int pid = Convert.ToInt32(m.Groups[2].Value, 16);
                    using var idKey = usb.OpenSubKey(idName);
                    if (idKey == null) continue;
                    foreach (var inst in idKey.GetSubKeyNames())
                    {
                        using var instKey = idKey.OpenSubKey(inst);
                        using var devParams = instKey?.OpenSubKey("Device Parameters");
                        if (devParams?.GetValue("PortName") is not string portName || portName.Length == 0) continue;
                        var desc = instKey?.GetValue("FriendlyName") as string ?? "";
                        var (name, mode) = ClassifyPort(vid, pid);
                        // v0.9.53 — presence comes from the PnP manager, not from SERIALCOMM
                        var present = IsDevicePresent(DeviceInstanceId(idName, inst));
                        // v0.9.51 — history rows keep their registry path so the cleanup can delete them
                        rows.Add(new(portName, desc, vid, pid, inst, name, mode, vid == 0x2341,
                                     IsHistoryRow(present, portName, live),
                                     $@"SYSTEM\CurrentControlSet\Enum\USB\{idName}\{inst}"));
                    }
                }
            }
        }
        catch { /* registry denied — fall through to the plain port list */ }
        try
        {
            using var comm = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"HARDWARE\DEVICEMAP\SERIALCOMM");
            if (comm != null)
                foreach (var valueName in comm.GetValueNames())
                {
                    if (comm.GetValue(valueName) is not string port || port.Length == 0) continue;
                    if (rows.Any(r => string.Equals(r.Device, port, StringComparison.OrdinalIgnoreCase))) continue;
                    rows.Add(new(port, valueName, 0, 0, "", null, null, false));
                }
        }
        catch { /* no ports at all — the empty list tells the story */ }
        return rows.OrderBy(r => r.Device, StringComparer.OrdinalIgnoreCase).ToList();
    }

    /// <summary>v0.9.51 — ports attached right now: HARDWARE\DEVICEMAP\SERIALCOMM only lists
    /// currently-attached serial devices, so it is the live set driving phantom detection.
    /// strict=true rethrows registry errors (the elevated cleanup refuses to run blind).</summary>
    public static HashSet<string> LiveSerialCommPorts(bool strict = false)
    {
        var live = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (!OperatingSystem.IsWindows()) return live;
        try
        {
            using var comm = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"HARDWARE\DEVICEMAP\SERIALCOMM");
            if (comm != null)
                foreach (var valueName in comm.GetValueNames())
                    if (comm.GetValue(valueName) is string port && port.Length > 0)
                        live.Add(port);
        }
        catch when (!strict) { /* registry denied — the caller decides how much it trusts the empty set */ }
        // v0.9.53 — SERIALCOMM alone misses composite CDC/modem interfaces, so union the
        // driver-visible names too. This set is now only a fallback for presence detection.
        try { foreach (var n in System.IO.Ports.SerialPort.GetPortNames()) live.Add(n); }
        catch { /* no serial stack — the registry answer stands */ }
        return live;
    }

    /// <summary>v0.9.51 — a registry row is history ("phantom") when its assigned port is not
    /// in the live set, i.e. the board is not attached right now.</summary>
    public static bool IsPhantom(string portName, ISet<string> livePorts) => !livePorts.Contains(portName);

    /// <summary>v0.9.51 — every VID/PID pair this tool can create (six CDC presets, the
    /// programmer identities) — the default scope of the history cleanup.</summary>
    public static HashSet<(int Vid, int Pid)> KnownVidPidSet() => KnownIdentities.Keys.ToHashSet();


    // ──────── v0.9.53 — real presence detection (the reference tool used SetupAPI via pyserial) ────────

    private const string Bs = @"\";

    /// <summary>v0.9.53 — Windows device instance id of one Enum-USB row, e.g.
    /// USB then VID_2341&amp;PID_8036&amp;MI_00 then 6&amp;299f51fa&amp;0&amp;0000. Pure (TestRunner step 53).</summary>
    public static string DeviceInstanceId(string idName, string instance)
    {
        if (string.IsNullOrWhiteSpace(idName) || string.IsNullOrWhiteSpace(instance)) return "";
        return "USB" + Bs + idName.Trim() + Bs + instance.Trim();
    }

    [System.Runtime.InteropServices.DllImport("cfgmgr32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    private static extern int CM_Locate_DevNodeW(out uint pdnDevInst, string pDeviceID, uint ulFlags);

    /// <summary>v0.9.53 — true when the PnP manager can locate this instance as an attached
    /// device (exactly what pyserial/SetupAPI report in the reference tool); false when it only
    /// exists as a phantom devnode; null when cfgmgr32 cannot answer.</summary>
    public static bool? IsDevicePresent(string instanceId)
    {
        if (!OperatingSystem.IsWindows() || string.IsNullOrWhiteSpace(instanceId)) return null;
        try
        {
            if (CM_Locate_DevNodeW(out _, instanceId, 0u) == 0) return true;    // NORMAL = present only
            if (CM_Locate_DevNodeW(out _, instanceId, 1u) == 0) return false;   // PHANTOM = known, detached
            return false;
        }
        catch { return null; }
    }

    /// <summary>v0.9.53 — history decision. PnP presence wins; the SERIALCOMM/driver name set is
    /// only the fallback, because composite CDC and modem interfaces are frequently absent from
    /// SERIALCOMM while attached — the root cause of the wrong history marks in v0.9.52.</summary>
    public static bool IsHistoryRow(bool? present, string portName, ISet<string> live)
    {
        if (present is bool p) return !p;
        return !live.Contains(portName);
    }

    /// <summary>v0.9.53 — how the current scan decided presence, for the log line.</summary>
    public static string PresenceSource(bool? probe) => probe is null ? "SERIALCOMM (fallback)" : "PnP (cfgmgr32)";

    /// <summary>v0.9.54 - what the port list shows. By default only attached ports, exactly
    /// like the reference tool (which listed present devices): the registry history rows made
    /// the list unreadable (10-21 rows for one board). History stays one switch away and is
    /// still counted, because the cleanup step needs it.</summary>
    public static List<PortInfo> VisibleRows(IReadOnlyList<PortInfo> rows, bool showHistory)
        => (showHistory ? rows : rows.Where(r => !r.IsPhantom)).ToList();

    /// <summary>v0.9.54 - the log line for a scan: attached count first, hidden history after.</summary>
    public static string ScanSummaryLine(IReadOnlyList<PortInfo> rows, bool showHistory)
    {
        int live = rows.Count(r => !r.IsPhantom);
        int hist = rows.Count - live;
        if (showHistory)
            return $"اسکن: {live} پورت وصل + {hist} ورودی تاریخچه (نمایش تاریخچه روشن است)";
        var tail = hist > 0
            ? $" — {hist} ورودی تاریخچه پنهان شد (با تیک «نمایش تاریخچه» دیده می‌شود)"
            : "";
        return $"اسکن: {live} پورت وصل پیدا شد" + tail;
    }

    /// <summary>v0.9.51 — phantom rows of allowed families; rows without a registry path
    /// (plain SERIALCOMM entries) can never be cleanup targets.</summary>
    public static List<PortInfo> PhantomBoardsOfKnownFamilies(IReadOnlyList<PortInfo> rows, ISet<(int Vid, int Pid)> allowed)
        => rows.Where(r => r.IsPhantom && r.RegPath.Length > 0 && allowed.Contains((r.Vid, r.Pid))).ToList();

    /// <summary>v0.9.51 — one list row for the checkup tab; history rows carry a visible
    /// marker. (Moved from the window so TestRunner can cover the marker.)</summary>
    public static string DescribePort(PortInfo r)
    {
        var phantom = r.IsPhantom ? "  🕘 تاریخچه (وصل نیست)" : "";
        if (r.Vid == 0) return $"{r.Device} — {r.Description}{phantom}";
        var identity = r.Identity is not null ? $" · {r.Identity} · {r.Mode}" : "";
        var serial = r.Serial.Length > 0 ? $" · s/n {r.Serial}" : "";
        return $"{r.Device} — {r.Description}  ({r.Vid:X4}:{r.Pid:X4}{identity}{serial}){phantom}";
    }

    /// <summary>Programmer-port preference: an ArduinoISP-sketch board (Leonardo identity
    /// 0x2341) first, else the first port — same rule as the original tool.</summary>
    public static string? PickProgrammerPort(IReadOnlyList<PortInfo> ports)
    {
        foreach (var p in ports)
            if (p.Vid == 0x2341 && p.Pid is 0x8036 or 0x8037 or 0x0036) return p.Device;
        return ports.Count > 0 ? ports[0].Device : null;
    }

    /// <summary>Sends the firmware-1.6 HELLO frame and reads the reply line; null when no
    /// answer arrives in time. v0.9.50 fix: the original tool sent "001|HELLO|" which
    /// firmware 1.6 never recognises — this port speaks the real frame HELLO|&lt;32 hex
    /// chars&gt; and only reads the unencrypted reply line (no session is opened).</summary>
    public static string? Handshake(string port, int baud = AmsBaud, double timeoutSec = 2.0)
    {
        if (!OperatingSystem.IsWindows()) return null;
        try
        {
            using var s = new System.IO.Ports.SerialPort(port, baud)
            {
                WriteTimeout = 1000,
                DtrEnable = true,   // same as pyserial — a 32U4 resets when the port opens
            };
            s.Open();
            try
            {
                Thread.Sleep(2000);   // wait out the reset — the proven tool does the same
                s.DiscardInBuffer();
                s.Write("HELLO|" + GenerateNonce32Hex() + "\n");
                var deadline = DateTime.UtcNow.AddSeconds(timeoutSec);
                var buf = new StringBuilder();
                while (DateTime.UtcNow < deadline)
                {
                    var chunk = s.ReadExisting();
                    if (chunk.Length > 0)
                    {
                        buf.Append(chunk);
                        if (chunk.Contains('\n')) break;
                    }
                    else Thread.Sleep(50);
                }
                var text = buf.ToString().Trim();
                return text.Length > 0 ? text : null;
            }
            finally { s.Close(); }
        }
        catch { return null; }
    }

    private static string GenerateNonce32Hex()
    {
        const string HexChars = "0123456789abcdef";
        var chars = new char[32];
        for (int i = 0; i < chars.Length; i++) chars[i] = HexChars[Random.Shared.Next(16)];
        return new string(chars);
    }

    /// <summary>Health summary messages: (icon, Persian text). Faithful port of the
    /// original tool's summarize_checkup. The handshakes dictionary maps device → reply
    /// (null when probed but silent); devices absent from it were never probed.</summary>
    public static List<(string Icon, string Text)> SummarizeCheckup(IReadOnlyList<PortInfo> rows,
                                                                    IReadOnlyDictionary<string, string?> handshakes)
    {
        var outMsgs = new List<(string, string)>();
        // v0.9.51 — history rows are excluded from the online view and listed separately
        var live = rows.Where(r => !r.IsPhantom).ToList();
        var boards = live.Where(r => r.Identity is not null && !r.IsProgrammer).ToList();
        var prog = live.Where(r => r.IsProgrammer).ToList();
        var phantoms = rows.Where(r => r.IsPhantom).ToList();
        if (prog.Count > 0)
            outMsgs.Add(("🛠", $"برد پروگرمر آنلاین است ({string.Join(", ", prog.Select(r => r.Device))})"));
        if (phantoms.Count > 0)
            outMsgs.Add(("🕘", $"{phantoms.Count} ورودی تاریخچه (وصل نیستند): {string.Join("، ", phantoms.Select(p => p.Device))} — با دکمه‌ی «پاکسازی تاریخچه‌ی COM» حذفشان می‌کنی"));
        if (rows.Count == 0)
        {
            outMsgs.Add(("✗", "هیچ پورت سریالی پیدا نشد — کابل/پورت را چک کن (کابل شارژری دیتا ندارد!)"));
            return outMsgs;
        }
        if (boards.Count == 0)
        {
            outMsgs.Add(("✗", phantoms.Count > 0
                ? "برد AMS وصل نیست — فقط ورودی‌های تاریخچه دیده می‌شوند؛ اول برد را وصل کن"
                : "برد AMS پیدا نشد — یا وصل نیست یا هویتش ناشناخته است"));
            return outMsgs;
        }
        foreach (var r in boards)
        {
            var d = r.Device;
            outMsgs.Add(("✓", $"{d}: هویت سفارشی فعال است ({r.Identity}، {r.Vid:X4}:{r.Pid:X4}) — ردپای Arduino دیده نمی‌شود"));
            if (r.Serial.Length > 0)
                outMsgs.Add(("✓", $"{d}: سریال‌نامبر یکتا تعبیه شده: {r.Serial}"));
            if (r.Mode == "بوت‌لودر")
                outMsgs.Add(("⚠", $"{d}: در حالت بوت‌لودر است — اسکچ روی برد نیست یا پورت موقت است؛ اسکچ را از IDE آپلود کن تا پورت پایدار شود"));
            else if (r.Mode == "اپلیکیشن")
                outMsgs.Add(("✓", $"{d}: در حالت اپلیکیشن است — اسکچ در حال اجراست"));
            if (handshakes.TryGetValue(d, out var ans))
            {
                if (!string.IsNullOrEmpty(ans))
                    outMsgs.Add(("✓", $"{d}: فیرمور به HELLO جواب داد ← «{ans}» — پروتکل AMS زنده است"));
                else
                    outMsgs.Add(("i", $"{d}: پاسخی به HELLO نیامد — طبیعی است اگر برد در بوت‌لودر باشد یا فیرمور هنوز پروتکل را پیاده نکرده باشد"));
            }
        }
        return outMsgs;
    }
}

/// <summary>v0.9.50 — locates bundled companion files (caterina\Caterina.hex,
/// tools\isp_flash.py) the same way the bridge script is found: in a subfolder next to
/// the exe, flat beside it, or by walking up the repo tree.</summary>
public static class BundledAssets
{
    public static List<string> Candidates(string baseDir, string subfolder, string name)
    {
        string trimmed = baseDir.TrimEnd(Path.DirectorySeparatorChar);
        var list = new List<string>
        {
            Path.Combine(trimmed, subfolder, name),   // build output (csproj link copy)
            Path.Combine(trimmed, name),              // flat publish folder
        };
        var dir = new DirectoryInfo(trimmed);
        for (int i = 0; i < 4 && dir?.Parent is not null; i++, dir = dir.Parent)
        {
            list.Add(Path.Combine(dir.Parent.FullName, subfolder, name));
            list.Add(Path.Combine(dir.Parent.FullName, "ams-shell", subfolder, name));   // exe inside the repo tree
        }
        return list;
    }

    public static string? Find(string baseDir, string subfolder, string name)
        => Candidates(baseDir, subfolder, name).FirstOrDefault(File.Exists);
}
