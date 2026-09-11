using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Cycle-aware firmware export layered on the hardware-proven Pico template.</summary>
public static class AutoCycleFirmwareBundle
{
    private static readonly string[] RuntimeFiles =
        { "plan_cycle.py", "cycle_runtime.py", "restart_windows.py", "auto_resume_boot.py" };

    public static IReadOnlyList<string> Export(string codePyPath, IEnumerable<StepNode> steps,
        string machine, string loopMode, int loopCount, int loopSeconds, bool keyboardOnArm)
    {
        var runtimeDir = Path.Combine(AppContext.BaseDirectory, "portable-runtime");
        foreach (var name in RuntimeFiles)
            if (!File.Exists(Path.Combine(runtimeDir, name)))
                throw new IOException("فایل runtime چرخه پیدا نشد: " + name);

        var written = PicoFirmwareExporter.Export(codePyPath, steps, machine,
            loopMode, loopCount, loopSeconds, keyboardOnArm).ToList();
        var full = Path.GetFullPath(codePyPath);
        var dir = Path.GetDirectoryName(full) ?? throw new IOException("مسیر firmware نامعتبر است.");
        var patched = PatchCode(File.ReadAllText(full));

        var payloads = new List<(string Path, byte[] Bytes)>
        {
            (full, new UTF8Encoding(false).GetBytes(patched)),
        };
        foreach (var name in RuntimeFiles)
            payloads.Add((Path.Combine(dir, name), File.ReadAllBytes(Path.Combine(runtimeDir, name))));
        PublishAtomically(payloads);
        written.AddRange(RuntimeFiles.Select(name => Path.Combine(dir, name)));
        return written.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static string PatchCode(string code)
    {
        code = ReplaceOnce(code,
            "try:\n    import plan_engine as _pe\nexcept Exception:\n    _pe = None",
            "try:\n    import plan_engine as _pe\n    import plan_cycle as _pc\n    from cycle_runtime import ResumeArmStore\n    from auto_resume_boot import AutoResumeBoot\nexcept Exception as _cycle_import_error:\n    _pe = None\n    _pc = None\n    print('cycle: import failed:', _cycle_import_error)");

        code = ReplaceOnce(code,
            "                    _plan_cache = _pe.parse_plan(text)\n                    print(\"plan: loaded\", len(_plan_cache), \"ops\")",
            "                    _ops, _policy = _pc.parse_cycle_plan(text)\n                    _plan_cache = text\n                    print(\"plan: loaded\", len(_ops), \"ops\")");

        code = ReplaceOnce(code,
            "                _pe.run_plan(_plan_cache, _PlanCtx())\n                return \"done\"",
            "                _cycle_result = _pc.run_root(_plan_cache, _PlanCtx(), arm_store=_resume_store)\n                return \"done\" if _cycle_result == \"finished\" else _cycle_result");

        code = ReplaceOnce(code,
            "\n\n        def plan_pass():",
            ContextAndBootSupport + "\n\n        def plan_pass():");

        code = ReplaceOnce(code,
            "        buffer = bytearray()               # v0.9.60 - bounded byte buffer, not string concat",
            BootInitialization + "\n\n        buffer = bytearray()               # v0.9.60 - bounded byte buffer, not string concat");

        code = ReplaceOnce(code,
            "                    poll_keypad()\n                    host_quiet = time.monotonic() - last_host_cmd >= 3",
            "                    _resume_boot.tick()    # armed reboot: wait for USB host + randomized settle\n                    poll_keypad()             # GP4 can cancel the wait and start manually\n                    host_quiet = time.monotonic() - last_host_cmd >= 3");

        code = ReplaceOnce(code,
            "            if line in (\"HALT\", \"BYE\"):\n                _flow_reset()",
            "            if line in (\"HALT\", \"BYE\"):\n                try:\n                    _resume_store.clear()\n                except Exception:\n                    pass\n                _flow_reset()");
        return code;
    }

    private static string ReplaceOnce(string text, string oldText, string newText)
    {
        var first = text.IndexOf(oldText, StringComparison.Ordinal);
        if (first < 0 || text.IndexOf(oldText, first + oldText.Length, StringComparison.Ordinal) >= 0)
            throw new InvalidDataException("قالب firmware با قرارداد چرخه همگام نیست: " + oldText.Split('\n')[0]);
        return text[..first] + newText + text[(first + oldText.Length)..];
    }

    private const string ContextAndBootSupport = """

            def gate(self):
                pump_arm()
                poll_keypad()
                return engine_on

            def key_combo(self, values, hold_min=0, hold_max=0):
                body = "+".join((str(v) for v in values))
                handle_keyboard("KCOMBO|%s,%d,%d" % (body, hold_min, hold_max), "KCOMBO")

            def kdown(self, vk):
                handle_keyboard("KDOWN|%d" % vk, "KDOWN")

            def kup(self, vk):
                handle_keyboard("KUP|%d" % vk, "KUP")

            def wheel(self, delta):
                forward_fast("MWHEEL|%d" % delta)

            def raw(self, line):
                return handle(line)

            def read_plan_file(self, name):
                with open("/" + name, "r") as fh:
                    return fh.read()

            def release_all(self):
                try:
                    kbd.release_all()
                except Exception:
                    pass
                release_all_buttons(force=True)

            def halt(self):
                self.release_all()

        """;

    private const string BootInitialization = """
        _resume_store = ResumeArmStore("/.auto_resume_armed") if _pc is not None else None

        def _usb_host_ready():
            try:
                return bool(usb_cdc.console.connected)
            except Exception:
                return False

        def _auto_start_root():
            global engine_on, engine_paused
            engine_on = True
            engine_paused = False
            start_engine()
            print("cycle: AUTO_RESUME start")
            return True

        if _resume_store is not None:
            _resume_boot = AutoResumeBoot(_resume_store, time.monotonic, _usb_host_ready,
                                          _auto_start_root,
                                          lambda: btn1 is not None and not btn1.value)
            try:
                with open(PLAN_PATH, "r") as _cycle_fh:
                    _cycle_text = _cycle_fh.read()
                _cycle_ops, _cycle_policy = _pc.parse_cycle_plan(_cycle_text)
                if _cycle_policy is not None:
                    _resume_boot.configure(_cycle_policy["auto"],
                                           _cycle_policy["resume"][0],
                                           _cycle_policy["resume"][1])
            except Exception as _resume_error:
                print("cycle: resume policy unavailable:", _resume_error)
        else:
            class _NoResume:
                def tick(self):
                    return 0
            _resume_boot = _NoResume()
        """;

    private static void PublishAtomically(IReadOnlyList<(string Path, byte[] Bytes)> payloads)
    {
        var tx = Guid.NewGuid().ToString("N");
        var temps = payloads.Select(p => p.Path + "." + tx + ".tmp").ToArray();
        var backups = payloads.Select(p => p.Path + "." + tx + ".bak").ToArray();
        var published = new List<int>();
        try
        {
            for (var i = 0; i < payloads.Count; i++) File.WriteAllBytes(temps[i], payloads[i].Bytes);
            for (var i = 0; i < payloads.Count; i++)
            {
                if (File.Exists(payloads[i].Path)) File.Move(payloads[i].Path, backups[i]);
                File.Move(temps[i], payloads[i].Path);
                published.Add(i);
            }
            foreach (var backup in backups) if (File.Exists(backup)) File.Delete(backup);
        }
        catch
        {
            foreach (var i in published.AsEnumerable().Reverse())
                if (File.Exists(payloads[i].Path)) File.Delete(payloads[i].Path);
            for (var i = 0; i < payloads.Count; i++)
                if (File.Exists(backups[i])) File.Move(backups[i], payloads[i].Path, true);
            throw;
        }
        finally
        {
            foreach (var file in temps.Concat(backups)) if (File.Exists(file)) File.Delete(file);
        }
    }
}
