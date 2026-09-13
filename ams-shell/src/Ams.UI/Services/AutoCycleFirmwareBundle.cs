using System.Text;
using System.Text.Json;
using Ams.UI.Models;
namespace Ams.UI.Services;
public static class AutoCycleFirmwareBundle
{
    private const string PatchManifest = "autocycle_h6_patch.json";
    private static readonly string[] RuntimeFiles={"plan_cycle.py","cycle_runtime.py","restart_windows.py","auto_resume_boot.py","resume_essentials_runtime.py"};
    public static IReadOnlyList<string> Export(string codePyPath,IEnumerable<StepNode> steps,string machine,string loopMode,int loopCount,int loopSeconds,bool keyboardOnArm)
    {
        var runtimeDir=Path.Combine(AppContext.BaseDirectory,"portable-runtime");
        foreach(var name in RuntimeFiles.Append(PatchManifest)) if(!File.Exists(Path.Combine(runtimeDir,name))) throw new IOException("فایل runtime چرخه پیدا نشد: "+name);
        var written=PicoFirmwareExporter.Export(codePyPath,steps,machine,loopMode,loopCount,loopSeconds,keyboardOnArm).ToList();
        var full=Path.GetFullPath(codePyPath); var dir=Path.GetDirectoryName(full)??throw new IOException("مسیر firmware نامعتبر است.");
        var patched=PatchCode(File.ReadAllText(full),Path.Combine(runtimeDir,PatchManifest));
        var payloads=new List<(string Path,byte[] Bytes)>{(full,new UTF8Encoding(false).GetBytes(patched))};
        foreach(var name in RuntimeFiles) payloads.Add((Path.Combine(dir,name),File.ReadAllBytes(Path.Combine(runtimeDir,name))));
        PublishAtomically(payloads); written.AddRange(RuntimeFiles.Select(name=>Path.Combine(dir,name))); return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }
    public static string PatchCode(string code,string manifestPath)
    {
        code=code.Replace("\r\n","\n").Replace('\r','\n');
        code=NormalizeBuzzerForManifest(code);
        code=NormalizeMouseReliabilityForManifest(code);
        var manifest=JsonSerializer.Deserialize<PatchDocument>(File.ReadAllText(manifestPath),new JsonSerializerOptions { PropertyNameCaseInsensitive = true })??throw new InvalidDataException("manifest چرخه قابل خواندن نیست.");
        if(manifest.Version!=1||manifest.Edits.Count==0)throw new InvalidDataException("نسخه یا محتوای manifest چرخه معتبر نیست.");
        if(!code.Contains(manifest.Baseline,StringComparison.Ordinal))throw new InvalidDataException("Firmware پایه h6 مورد انتظار پیدا نشد: "+manifest.Baseline);
        foreach(var edit in manifest.Edits)code=ReplaceOnce(code,edit.Old,edit.New);
        code=PreserveKtextWhitespace(code);
        code=ApplyMouseReliabilityAfterManifest(code);
        foreach(var marker in RequiredMarkers)if(!code.Contains(marker,StringComparison.Ordinal))throw new InvalidDataException("پست‌کاندیشن Firmware چرخه پیدا نشد: "+marker);
        code=code.Replace("tone = pwmio.PWMOut(board.GP6,","tone = pwmio.PWMOut(board."+BuzzerGpioPolicy.Require(AppSettings.Load().BuzzerGpio)+",",StringComparison.Ordinal);
        return code;
    }
    // The AutoCycle manifest intentionally targets the accepted 0.9.64f baseline.
    // Normal export now hardens MCLICK/HOSTUSB first, so temporarily normalize only those
    // fragments, apply the manifest, then reapply the reliability contract to its output.
    private static string NormalizeMouseReliabilityForManifest(string code)
    {
        code=code.Replace("FAST_MOUSE_PREFIXES = (\"MMOVE\", \"MWHEEL\", \"MDOWN\", \"MUP\")",
                          "MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\", \"MWHEEL\", \"MDOWN\", \"MUP\")",StringComparison.Ordinal);
        code=RequireReplace(code,"parts[1] in FAST_MOUSE_PREFIXES","parts[1] in MOUSE_PREFIXES","normal mouse ACK filter");
        code=code.Replace("_last_hostusb_event = [None]  # forward identical HOSTUSB heartbeats once\n","",StringComparison.Ordinal);
        const string reliableEvent="        if line.startswith(\"EVT|\"):\n            if line.startswith(\"EVT|HOSTUSB|\"):\n                if line == _last_hostusb_event[0]:\n                    continue\n                _last_hostusb_event[0] = line\n            _serial_write_line(line)              # changed events reach the PC once\n            continue";
        const string legacyEvent="        if line.startswith(\"EVT|\"):\n            _serial_write_line(line)              # arm events reach the PC live\n            continue";
        code=RequireReplace(code,reliableEvent,legacyEvent,"normal HOSTUSB baseline");
        var helperStart=code.IndexOf("def _mclick_timeout(line):",StringComparison.Ordinal);
        var sampleStart=helperStart>=0?code.IndexOf("def sample():",helperStart,StringComparison.Ordinal):-1;
        if(helperStart<0||sampleStart<0)throw new InvalidDataException("MCLICK timeout helper baseline پیدا نشد.");
        code=code.Remove(helperStart,sampleStart-helperStart);
        const string reliableDispatch="    if head == \"MCLICK\":\n        return forward_to_arm(line, _mclick_timeout(line))\n    if head in FAST_MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        const string legacyDispatch="    if head in MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        code=RequireReplace(code,reliableDispatch,legacyDispatch,"normal MCLICK dispatch");
        return code;
    }
    private static string ApplyMouseReliabilityAfterManifest(string code)
    {
        code=RequireReplace(code,
            "MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\", \"MWHEEL\", \"MDOWN\", \"MUP\")",
            "FAST_MOUSE_PREFIXES = (\"MMOVE\", \"MWHEEL\", \"MDOWN\", \"MUP\")","cycle mouse prefixes");
        code=RequireReplace(code,"parts[1] in MOUSE_PREFIXES","parts[1] in FAST_MOUSE_PREFIXES","cycle mouse ACK filter");
        const string helper="def _mclick_timeout(line):\n    \"\"\"Physical-completion timeout for all randomized holds and inter-click gaps.\"\"\"\n    try:\n        fields = line.split(\"|\", 1)[1].split(\",\")\n        count = max(1, int(fields[1])) if len(fields) > 1 else 1\n        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45\n        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin\n        return max(5.0, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)\n    except Exception:\n        return 5.0\n\n\n";
        code=RequireReplace(code,"def sample():",helper+"def sample():","cycle MCLICK timeout helper");
        const string legacyDispatch="    if head in MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        const string reliableDispatch="    if head == \"MCLICK\":\n        return forward_to_arm(line, _mclick_timeout(line))\n    if head in FAST_MOUSE_PREFIXES:\n        return forward_fast(line)\n    if head in ARM_PREFIXES:";
        code=RequireReplace(code,legacyDispatch,reliableDispatch,"cycle MCLICK dispatch");
        return code;
    }
    private static string RequireReplace(string text,string oldText,string newText,string label)
    {
        if(text.CountOccurrences(oldText)!=1)throw new InvalidDataException("قرارداد "+label+" یکتا نیست.");
        return text.Replace(oldText,newText,StringComparison.Ordinal);
    }
    // A KTEXT payload may intentionally end with a literal space: in typo-correction
    // mode the planner flushes the text before the slip and then retypes the remainder.
    // The old line parser used strip(), deleting that trailing separator before HID saw it.
    private static string PreserveKtextWhitespace(string code)
    {
        const string oldLine="line = raw.decode(\"utf-8\", \"replace\").strip()";
        const string newLine="line = raw.decode(\"utf-8\", \"replace\").rstrip(\"\\r\")";
        return code.Replace(oldLine,newLine,StringComparison.Ordinal);
    }
    private static string NormalizeBuzzerForManifest(string code)
    {
        const string beep="    if line.startswith(\"BEEP|\"):";
        const string halt="    if line in (\"HALT\", \"BYE\"):";
        const string trigger="    if line.startswith(\"TRGLUX|\"):";
        var start=code.IndexOf(beep,StringComparison.Ordinal);
        if(start<0)return code;
        var end=code.IndexOf(halt,start,StringComparison.Ordinal);
        var destination=code.IndexOf(trigger,StringComparison.Ordinal);
        if(end<0||destination<0||destination>start)throw new InvalidDataException("قالب BEEP firmware قابل همگام‌سازی نیست.");
        var block=code[start..end];
        code=code.Remove(start,end-start);
        destination=code.IndexOf(trigger,StringComparison.Ordinal);
        code=code.Insert(destination,block);
        var planGp6="tone = pwmio.PWMOut(board."+BuzzerGpioPolicy.Require(AppSettings.Load().BuzzerGpio)+", duty_cycle=0,\n                                frequency=int(freq)";
        const string planGp5="tone = pwmio.PWMOut(board.GP5, duty_cycle=0,\n                                frequency=int(freq)";
        if(code.CountOccurrences(planGp6)!=1)throw new InvalidDataException("قالب GP6 plan beep قابل همگام‌سازی نیست.");
        return code.Replace(planGp6,planGp5,StringComparison.Ordinal);
    }
    private static int CountOccurrences(this string text,string value){var count=0;var at=0;while((at=text.IndexOf(value,at,StringComparison.Ordinal))>=0){count++;at+=value.Length;}return count;}
    private static readonly string[] RequiredMarkers={"AUTO_CYCLE_PATCH_0967_H6","import supervisor","import plan_cycle as _pc","from auto_resume_boot import AutoResumeBoot","EVT|HOSTUSB|","usb_down=_usb_host_down","_resume_boot.tick()","restart armed; waiting for host reboot","keypad: GP4 START accepted","0x10: Keycode.LEFT_SHIFT"};
    private static string ReplaceOnce(string text,string oldText,string newText)
    {
        if(string.IsNullOrEmpty(oldText))throw new InvalidDataException("anchor خالی در manifest چرخه.");
        var first=text.IndexOf(oldText,StringComparison.Ordinal);
        var duplicate=first>=0&&text.IndexOf(oldText,first+oldText.Length,StringComparison.Ordinal)>=0;
        if(!duplicate&&first>=0)return text[..first]+newText+text[(first+oldText.Length)..];
        const string beepMarker="    def beep(self, freq, ms):";
        const string beepEnd="            if not _plan_sleep_ms(int(ms)):\n";
        var oldBeep=text.IndexOf(beepMarker,StringComparison.Ordinal);
        var oldBeepEnd=oldBeep>=0?text.IndexOf(beepEnd,oldBeep,StringComparison.Ordinal):-1;
        var newRelease=newText.IndexOf("    def release_all(self):",StringComparison.Ordinal);
        var newBeepEnd=newRelease>=0?newText.IndexOf(beepEnd,newRelease,StringComparison.Ordinal):-1;
        if(oldBeep>=0&&oldBeepEnd>=0&&newRelease>=0&&newBeepEnd>=0
            &&text.IndexOf(beepMarker,oldBeep+beepMarker.Length,StringComparison.Ordinal)<0)
        {
            var replacement=newText[newRelease..(newBeepEnd+beepEnd.Length)];
            return text[..oldBeep]+replacement+text[(oldBeepEnd+beepEnd.Length)..];
        }
        var reason=first<0?"anchor missing":"anchor is not unique";
        throw new InvalidDataException("قالب firmware با قرارداد چرخه همگام نیست ("+reason+"): "+oldText.Split('\n')[0]);
    }
    private sealed class PatchDocument{public int Version{get;set;}public string Baseline{get;set;}="";public List<PatchEdit> Edits{get;set;}=new();}
    private sealed class PatchEdit{public string Old{get;set;}="";public string New{get;set;}="";}
    private static void PublishAtomically(IReadOnlyList<(string Path,byte[] Bytes)> payloads){var tx=Guid.NewGuid().ToString("N");var temps=payloads.Select(p=>p.Path+"."+tx+".tmp").ToArray();var backups=payloads.Select(p=>p.Path+"."+tx+".bak").ToArray();var published=new List<int>();try{for(var i=0;i<payloads.Count;i++)File.WriteAllBytes(temps[i],payloads[i].Bytes);for(var i=0;i<payloads.Count;i++){if(File.Exists(payloads[i].Path))File.Move(payloads[i].Path,backups[i]);File.Move(temps[i],payloads[i].Path);published.Add(i);}foreach(var b in backups)if(File.Exists(b))File.Delete(b);}catch{foreach(var i in published.AsEnumerable().Reverse())if(File.Exists(payloads[i].Path))File.Delete(payloads[i].Path);for(var i=0;i<payloads.Count;i++)if(File.Exists(backups[i]))File.Move(backups[i],payloads[i].Path,true);throw;}finally{foreach(var f in temps.Concat(backups))if(File.Exists(f))File.Delete(f);}}
}
