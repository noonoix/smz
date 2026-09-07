// v0.9.51 — COM-port history cleanup for the board-preparation checkup tab. The app side
// (non-elevated) lists phantom ports and writes a one-shot request file; the elevated side
// runs a headless relaunch ("--com-cleanup <request.json>", Verb=runas) that backs up the
// affected keys, deletes ONLY phantom instances of known VID/PID families, and frees their
// bits in the COM Name Arbiter bitmap. Golden rule honoured: every namespace is imported
// explicitly — implicit usings are not trusted on the build machine (lesson v0.9.50c).
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Win32;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Runtime.InteropServices;

namespace Ams.UI.Services;

/// <summary>v0.9.51 — deletes stale (phantom) COM-port history entries that Windows keeps
/// for every USB-serial board ever attached. Scope guard rails: only registry instance
/// paths under Enum\USB, only allow-listed VID/PID families, only ports that are still
/// phantom at execution time, and a .reg backup before anything is removed.</summary>
public static class BoardCleanupService
{
    public const string CleanupArg = "--com-cleanup";
    public const string RequestFileName = "com-cleanup-request.json";
    public const string ResultFileName = "com-cleanup-result.log";
    public const string ArbiterPath = @"SYSTEM\CurrentControlSet\Control\COM Name Arbiter";
    private const string EnumUsbPrefix = @"SYSTEM\CurrentControlSet\Enum\USB\";

    public sealed record CleanupItem(string RegPath, int Port);
    public sealed record CleanupRequest(List<CleanupItem> Items, List<string> AllowedVidPid, string BackupDir, string LogPath);

    // ───────────────────────── pure helpers (TestRunner step 51) ─────────────────────────

    /// <summary>"COM13" → 13; −1 when the name is not a numbered COM port (or COM0).</summary>
    public static int PortNumber(string device)
    {
        var m = Regex.Match(device ?? "", @"^COM(\d+)$", RegexOptions.IgnoreCase);
        if (!m.Success) return -1;
        return int.TryParse(m.Groups[1].Value, out var n) && n > 0 ? n : -1;
    }

    /// <summary>Clears the bits of freed ports in the COM Name Arbiter bitmap
    /// (bit index = port number − 1, so COM17 = byte 2 bit 0). Out-of-range ports are ignored.</summary>
    public static byte[] ClearComDbBits(byte[] comDb, IEnumerable<int> ports)
    {
        var copy = (byte[])comDb.Clone();
        foreach (var n in ports)
        {
            if (n < 1 || n > 256) continue;
            int bit = n - 1;
            int idx = bit >> 3;
            if (idx >= copy.Length) continue;
            copy[idx] &= (byte)~(1 << (bit & 7));
        }
        return copy;
    }

    // v0.9.53 — composite boards expose function suffixes (&MI_00), which the v0.9.51 pattern
    // rejected outright: every such entry was logged as "outside the allowed families" and skipped.
    private static readonly Regex RegPathRe = new(
        @"^SYSTEM\\CurrentControlSet\\Enum\\USB\\(VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})(?:&[^\\]*)?)\\([^\\]+)$",
        RegexOptions.Compiled | RegexOptions.IgnoreCase);

    private const string Bs = @"\";

    /// <summary>Parses VID/PID out of an Enum\USB instance path; null when the shape is wrong
    /// (root keys, other hives and non-USB subtrees never parse).</summary>
    public static (int Vid, int Pid)? VidPidFromRegPath(string regPath)
    {
        var m = RegPathRe.Match(regPath ?? "");
        if (!m.Success) return null;
        return (Convert.ToInt32(m.Groups[2].Value, 16), Convert.ToInt32(m.Groups[3].Value, 16));
    }

    /// <summary>v0.9.53 — the real parent key segment, suffix included, so the .reg backup
    /// exports the key that is actually being touched.</summary>
    public static string ParentKeyFromRegPath(string regPath)
    {
        var m = RegPathRe.Match(regPath ?? "");
        return m.Success ? m.Groups[1].Value : "";
    }

    /// <summary>v0.9.53 — the PnP device instance id of a history entry, used by pnputil.</summary>
    public static string InstanceIdFromRegPath(string regPath)
    {
        var m = RegPathRe.Match(regPath ?? "");
        return m.Success ? "USB" + Bs + m.Groups[1].Value + Bs + m.Groups[4].Value : "";
    }

    /// <summary>v0.9.53 — one family covers both firmware states (application PID = bootloader + 1
    /// and the reverse), so 1D50:615F is honoured when 1D50:615E is allow-listed.</summary>
    public static HashSet<(int Vid, int Pid)> ExpandFamilies(IEnumerable<(int Vid, int Pid)> allowed)
    {
        var set = new HashSet<(int Vid, int Pid)>();
        foreach (var a in allowed)
        {
            set.Add(a);
            if (a.Pid < 0xFFFF) set.Add((a.Vid, a.Pid + 1));
            if (a.Pid > 0) set.Add((a.Vid, a.Pid - 1));
        }
        return set;
    }

    /// <summary>v0.9.53 — removal ladder in order. Registry surgery is the LAST resort: the
    /// Enum-USB subtree is owned by SYSTEM and an elevated Administrators token carries
    /// SeTakeOwnershipPrivilege/SeRestorePrivilege in a DISABLED state, which is exactly why
    /// v0.9.52 logged "Attempted to perform an unauthorized operation" for every entry.</summary>
    public static string[] DeletePlan() => new[] { "pnputil", "privileged-registry", "system-task" };

    /// <summary>Defense in depth: a request item is only honoured when its path sits under
    /// Enum\USB AND its VID/PID pair is on the request's own allow-list.</summary>
    public static bool IsAllowedRegPath(string regPath, ISet<(int Vid, int Pid)> allowed)
    {
        var vp = VidPidFromRegPath(regPath);
        return vp is not null && allowed.Contains(vp.Value);
    }

    /// <summary>Parses the allow-list text form "1D50:615E".</summary>
    public static (int Vid, int Pid)? VidPidFromPairText(string text)
    {
        var m = Regex.Match(text ?? "", @"^([0-9A-Fa-f]{4})[:;]([0-9A-Fa-f]{4})$");
        if (!m.Success) return null;
        return (Convert.ToInt32(m.Groups[1].Value, 16), Convert.ToInt32(m.Groups[2].Value, 16));
    }

    // ───────────────────────── app side (non-elevated) ─────────────────────────

    public static string RequestPath(string exeDir) => Path.Combine(exeDir, RequestFileName);
    public static string ResultPath(string exeDir) => Path.Combine(exeDir, ResultFileName);

    public static void WriteRequest(string exeDir, CleanupRequest req)
        => File.WriteAllText(RequestPath(exeDir), JsonSerializer.Serialize(req));

    public static List<string> ReadResult(string exeDir)
    {
        var p = ResultPath(exeDir);
        return File.Exists(p)
            ? File.ReadAllLines(p).ToList()
            : new List<string> { "(نتیجه‌ای نوشته نشد — اجرای ادمین شکست خورد یا لغو شد)" };
    }

    /// <summary>Relaunches this exe elevated with the cleanup argument. Throws
    /// Win32Exception (1223) when the user declines the UAC prompt — the caller catches it.</summary>
    public static Process? RelaunchElevated(string exeDir)
    {
        var psi = new ProcessStartInfo
        {
            FileName = Environment.ProcessPath ?? Path.Combine(exeDir, "ClassroomStudio.exe"),
            Arguments = CleanupArg + " \"" + RequestPath(exeDir) + "\"",
            Verb = "runas",
            UseShellExecute = true,
        };
        return Process.Start(psi);
    }

    // ───────────────────────── elevated headless run ─────────────────────────

    /// <summary>Entry point of the elevated one-off run (called from App.OnStartup).
    /// Returns the process exit code: 0 = clean, 2 = partial, 1 = failed/aborted.</summary>
    public static int RunElevatedFromRequest(string? requestPath)
    {
        var log = new List<string> { "پاکسازی تاریخچه‌ی COM — اجرای ادمین " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") };
        string logPath = Path.Combine(AppContext.BaseDirectory, ResultFileName);

        int Run()
        {
            if (!OperatingSystem.IsWindows()) { log.Add("FAIL: پاکسازی فقط روی ویندوز معنا دارد"); return 1; }
            var reqPath = requestPath ?? RequestPath(AppContext.BaseDirectory);
            if (!File.Exists(reqPath)) { log.Add("FAIL: فایل درخواست پیدا نشد: " + reqPath); return 1; }
            var req = JsonSerializer.Deserialize<CleanupRequest>(File.ReadAllText(reqPath));
            if (req is null || req.Items.Count == 0) { log.Add("FAIL: درخواست خالی است"); return 1; }
            if (!string.IsNullOrWhiteSpace(req.LogPath)) logPath = req.LogPath;
            try { File.Delete(reqPath); } catch { /* one-shot request; a stale copy is harmless */ }

            var parsed = new List<(int Vid, int Pid)>();
            foreach (var s in req.AllowedVidPid)
            {
                var vp = VidPidFromPairText(s);
                if (vp is not null) parsed.Add(vp.Value);
            }
            var allowed = ExpandFamilies(parsed);   // v0.9.53 — bootloader and application PIDs

            // safety: the live set must be readable, otherwise nothing may be deleted
            HashSet<string> live;
            try { live = BoardCheckupService.LiveSerialCommPorts(strict: true); }
            catch (Exception ex)
            {
                log.Add("FAIL: فهرست پورت‌های وصل‌شده خوانده نشد — برای ایمنی هیچ حذفی انجام نمی‌شود (" + ex.Message + ")");
                return 1;
            }

            var targets = new List<CleanupItem>();
            foreach (var item in req.Items)
            {
                if (!IsAllowedRegPath(item.RegPath, allowed)) { log.Add("رد شد (خارج از خانواده‌های مجاز): " + item.RegPath); continue; }
                if (item.Port <= 0) { log.Add("رد شد (شماره‌ی پورت نامعتبر): " + item.RegPath); continue; }
                if (live.Contains("COM" + item.Port)) { log.Add($"رد شد (همین الان وصل است): COM{item.Port} — {item.RegPath}"); continue; }
                targets.Add(item);
            }
            if (targets.Count == 0) { log.Add("هیچ هدفی برای حذف نماند — تاریخچه همین حالا تمیز است"); return 0; }

            // 1) backup each affected VID&PID parent key BEFORE any deletion
            var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
            var backedParents = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            int bi = 0;
            foreach (var item in targets)
            {
                var parent = ParentKeyFromRegPath(item.RegPath);   // v0.9.53 — suffix-accurate
                if (!backedParents.Add(parent)) continue;
                var backupFile = Path.Combine(req.BackupDir, $"com-cleanup-backup-{stamp}-{bi++}-{parent.Replace('&', '_')}.reg");
                if (ExportKey(@"HKLM\" + EnumUsbPrefix.TrimEnd('\\') + "\\" + parent, backupFile, log) != 0)
                {
                    log.Add("FAIL: بکاپ گرفته نشد — هیچ حذفی انجام نشد");
                    return 1;
                }
                log.Add("بکاپ: " + backupFile);
            }

            // 2) delete the phantom instance keys
            int deleted = 0;
            var deletedPorts = new List<int>();
            foreach (var item in targets)
                if (DeleteHistoryEntry(item.RegPath, item.Port, log)) { deleted++; deletedPorts.Add(item.Port); }

            // 3) free the arbiter bits of the ports that really went away
            if (deletedPorts.Count > 0)
                ClearArbiterBits(deletedPorts, log);

            log.Add($"نتیجه: {deleted}/{targets.Count} ورودی تاریخچه حذف شد");
            return deleted == targets.Count ? 0 : 2;
        }

        int code;
        try { code = Run(); }
        catch (Exception ex) { log.Add("FAIL: " + ex.Message); code = 1; }
        try { File.WriteAllLines(logPath, log); } catch { /* nowhere else to report */ }
        return code;
    }


    // ──────── v0.9.53 — deletion ladder ────────

    private const string Q = "\"";

    private static string Quote(string s) => Q + s + Q;

    private static bool KeyExists(string regPath)
    {
        try { using var k = Registry.LocalMachine.OpenSubKey(regPath); return k is not null; }
        catch { return true; }   // cannot prove it is gone
    }

    private static int Exec(string exe, string args, List<string> log)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = exe,
                Arguments = args,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            using var p = Process.Start(psi);
            if (p is null) return 1;
            p.WaitForExit(60000);
            var err = p.StandardError.ReadToEnd().Trim();
            if (p.ExitCode != 0 && err.Length > 0) log.Add("i " + Path.GetFileName(exe) + ": " + err);
            return p.ExitCode;
        }
        catch (Exception ex) { log.Add("i " + Path.GetFileName(exe) + ": " + ex.Message); return 1; }
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Luid { public uint LowPart; public int HighPart; }

    [StructLayout(LayoutKind.Sequential)]
    private struct TokenPrivileges { public uint PrivilegeCount; public Luid Luid; public uint Attributes; }

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool LookupPrivilegeValueW(string? system, string name, out Luid luid);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll,
        ref TokenPrivileges newState, uint length, IntPtr previous, IntPtr returnLength);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);

    /// <summary>v0.9.53 — an elevated token HAS SeTakeOwnershipPrivilege and SeRestorePrivilege but
    /// they are disabled by default and .NET never enables them; without this call every ownership
    /// change on an Enum-USB key fails with "Attempted to perform an unauthorized operation".</summary>
    private static bool EnableRegistryPrivileges(List<string> log)
    {
        bool all = true;
        IntPtr token = IntPtr.Zero;
        try
        {
            if (!OpenProcessToken(Process.GetCurrentProcess().Handle, 0x0020u | 0x0008u, out token)) return false;
            foreach (var name in new[] { "SeTakeOwnershipPrivilege", "SeRestorePrivilege", "SeBackupPrivilege" })
            {
                if (!LookupPrivilegeValueW(null, name, out var luid)) { all = false; continue; }
                var tp = new TokenPrivileges { PrivilegeCount = 1, Luid = luid, Attributes = 0x00000002u };
                if (!AdjustTokenPrivileges(token, false, ref tp, (uint)Marshal.SizeOf<TokenPrivileges>(), IntPtr.Zero, IntPtr.Zero))
                    all = false;
            }
        }
        catch (Exception ex) { log.Add("i فعال‌سازی اختیارات رجیستری: " + ex.Message); all = false; }
        finally { if (token != IntPtr.Zero) CloseHandle(token); }
        return all;
    }

    /// <summary>v0.9.53 — last resort: run reg.exe as SYSTEM through a one-shot scheduled task.
    /// SYSTEM owns the Enum-USB subtree, so no ownership juggling is needed.</summary>
    private static bool DeleteViaSystemTask(string regPath, List<string> log)
    {
        try
        {
            var cmdFile = Path.Combine(Path.GetTempPath(), "com-cleanup-" + Guid.NewGuid().ToString("N") + ".cmd");
            var line = "reg delete " + Quote(@"HKLM\" + regPath) + " /f";
            File.WriteAllText(cmdFile, "@echo off" + Environment.NewLine + line + Environment.NewLine);
            var task = "AmsComCleanup" + DateTime.Now.ToString("HHmmssfff");
            var schtasks = Path.Combine(Environment.SystemDirectory, "schtasks.exe");
            if (Exec(schtasks, "/create /tn " + Quote(task) + " /tr " + Quote(cmdFile)
                     + " /sc once /st 00:00 /ru SYSTEM /rl HIGHEST /f", log) != 0) return false;
            Exec(schtasks, "/run /tn " + Quote(task), log);
            for (int i = 0; i < 20 && KeyExists(regPath); i++) System.Threading.Thread.Sleep(400);
            Exec(schtasks, "/delete /tn " + Quote(task) + " /f", log);
            try { File.Delete(cmdFile); } catch { /* temp file */ }
            return !KeyExists(regPath);
        }
        catch (Exception ex) { log.Add("i اجرای SYSTEM: " + ex.Message); return false; }
    }

    /// <summary>v0.9.53 — tries the ladder from DeletePlan() and reports which rung worked.</summary>
    private static bool DeleteHistoryEntry(string regPath, int port, List<string> log)
    {
        var instanceId = InstanceIdFromRegPath(regPath);
        if (instanceId.Length > 0)
        {
            var pnputil = Path.Combine(Environment.SystemDirectory, "pnputil.exe");
            Exec(pnputil, "/remove-device " + Quote(instanceId), log);
            if (!KeyExists(regPath)) { log.Add($"حذف شد (pnputil): COM{port} — {instanceId}"); return true; }
        }

        try
        {
            EnableRegistryPrivileges(log);
            TakeOwnershipAndDeleteTree(regPath, log);
            if (!KeyExists(regPath)) { log.Add($"حذف شد (مالکیت رجیستری): COM{port}"); return true; }
        }
        catch (Exception ex) { log.Add($"i مالکیت رجیستری برای COM{port} جواب نداد: " + ex.Message); }

        if (DeleteViaSystemTask(regPath, log)) { log.Add($"حذف شد (اجرای SYSTEM): COM{port}"); return true; }

        log.Add($"FAIL حذف COM{port}: هر سه روش (pnputil · مالکیت رجیستری · اجرای SYSTEM) شکست خورد");
        return false;
    }

    /// <summary>reg.exe export of one parent key — the undo path. No backup, no deletion.</summary>
    private static int ExportKey(string hklmPath, string backupFile, List<string> log)
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = Path.Combine(Environment.SystemDirectory, "reg.exe"),
                Arguments = $"export \"{hklmPath}\" \"{backupFile}\" /y",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            using var p = Process.Start(psi);
            if (p is null) return 1;
            p.WaitForExit();
            if (p.ExitCode != 0) log.Add("خطای reg.exe: " + p.StandardError.ReadToEnd().Trim());
            return p.ExitCode;
        }
        catch (Exception ex) { log.Add("خطای reg.exe: " + ex.Message); return 1; }
    }

    /// <summary>Enum\USB device keys are owned by SYSTEM, so the elevated run first takes
    /// ownership for the Administrators group, then grants full control, then deletes.
    /// The SID form (S-1-5-32-544) is language-independent — safe on Persian Windows.</summary>
    private static void TakeOwnershipAndDeleteTree(string regPath, List<string> log)
    {
        var admins = new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null);
        using (var key = Registry.LocalMachine.OpenSubKey(regPath, RegistryKeyPermissionCheck.ReadWriteSubTree, RegistryRights.TakeOwnership))
        {
            if (key is null) { log.Add("از قبل نیست: " + regPath); return; }
            var acl = key.GetAccessControl();
            acl.SetOwner(admins);
            key.SetAccessControl(acl);
        }
        using (var key = Registry.LocalMachine.OpenSubKey(regPath, RegistryKeyPermissionCheck.ReadWriteSubTree, RegistryRights.ChangePermissions))
        {
            if (key is null) { log.Add("از قبل نیست: " + regPath); return; }
            var acl = key.GetAccessControl();
            acl.ResetAccessRule(new RegistryAccessRule(admins, RegistryRights.FullControl,
                InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
                PropagationFlags.None, AccessControlType.Allow));
            key.SetAccessControl(acl);
        }
        Registry.LocalMachine.DeleteSubKeyTree(regPath, throwOnMissingSubKey: false);
        log.Add("حذف شد: " + regPath);
    }

    /// <summary>Clears the freed ports' bits in the COM Name Arbiter bitmap so Windows
    /// assigns the lowest free numbers again. Only the listed ports are touched.</summary>
    private static void ClearArbiterBits(IEnumerable<int> ports, List<string> log)
    {
        try
        {
            using var arb = Registry.LocalMachine.OpenSubKey(ArbiterPath, writable: true);
            if (arb?.GetValue("ComDB") is byte[] comDb)
            {
                var list = ports.Distinct().ToList();
                arb.SetValue("ComDB", ClearComDbBits(comDb, list), RegistryValueKind.Binary);
                log.Add("بیت‌مپ ComDB آزاد شد برای: " + string.Join("، ", list.Select(p => "COM" + p)));
            }
            else log.Add("i: مقدار ComDB پیدا نشد — چیزی برای آزادسازی نیست");
        }
        catch (Exception ex) { log.Add("FAIL ComDB: " + ex.Message); }
    }
}
