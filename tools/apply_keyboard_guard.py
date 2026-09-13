from pathlib import Path
import subprocess

PATH = Path("ams-shell/src/Ams.UI/Services/RunEngine.cs")
s = PATH.read_text(encoding="utf-8")
if s.strip() == "PLACEHOLDER":
    s = subprocess.check_output(
        ["git", "show", "a6b709d0b86ad666753732f31bdbcca441ed9820:" + PATH.as_posix()],
        text=True,
        encoding="utf-8",
    )

if "TryHandleKeyboardStateGuard" not in s:
    field_anchor = "    private readonly HashSet<string> _scriptStack = new(StringComparer.OrdinalIgnoreCase);\n"
    field_block = field_anchor + """    /// <summary>v0.9.68 — run-scoped explicit key state, isolated per keyboard route.
    /// Duplicate KDOWN is suppressed until the matching KUP. Access is locked because
    /// Parallel Group branches can execute keyboard steps concurrently.</summary>
    private readonly object _heldKeyboardLock = new();
    private readonly HashSet<string> _heldKeyboardKeys = new(StringComparer.Ordinal);
"""
    if s.count(field_anchor) != 1:
        raise SystemExit("RunEngine keyboard field anchor mismatch")
    s = s.replace(field_anchor, field_block, 1)

    reset_anchor = "        _parallelKeySeq = 0; _lastParallelKeyTick = 0; _mouseRestAtSeq = -1;   // v0.9.23 — reset typing signal\n"
    if s.count(reset_anchor) != 1:
        raise SystemExit("RunEngine keyboard reset anchor mismatch")
    s = s.replace(reset_anchor, reset_anchor + "        lock (_heldKeyboardLock) _heldKeyboardKeys.Clear();\n", 1)

    catch_anchor = """        catch (GotoSignal g)   // v0.8.3 — the jump found no label at ANY level: stop cleanly with a tip
        {
            _log($"⚠ go to label \\"{g.Label}\\" — label not found; script stopped");
        }
"""
    if s.count(catch_anchor) != 1:
        raise SystemExit("RunEngine cleanup anchor mismatch")
    s = s.replace(catch_anchor, catch_anchor + """        finally
        {
            await ReleaseHeldKeyboardKeysAsync();
        }
""", 1)

    send_anchor = """                            await Send(wireCmd, ct,
                                logAs: secret && cmd.StartsWith("KTEXT|") ? MaskKtext(cmd) : null);
"""
    if s.count(send_anchor) != 1:
        raise SystemExit("RunEngine guarded send anchor mismatch")
    s = s.replace(send_anchor, """                            if (TryHandleKeyboardStateGuard(wireCmd, out var guardedCmd, out var guardLog))
                            {
                                if (guardLog is not null) _log(guardLog);
                                if (guardedCmd is not null)
                                    await Send(guardedCmd, ct,
                                        logAs: secret && cmd.StartsWith("KTEXT|") ? MaskKtext(cmd) : null);
                            }
                            else
                            {
                                await Send(wireCmd, ct,
                                    logAs: secret && cmd.StartsWith("KTEXT|") ? MaskKtext(cmd) : null);
                            }
""", 1)

    helper_anchor = "    private async Task<string> Send(string cmd, CancellationToken ct, string? logAs = null,\n"
    helper = """    private bool TryHandleKeyboardStateGuard(string cmd, out string? guardedCmd, out string? guardLog)
    {
        guardedCmd = cmd;
        guardLog = null;
        string body = cmd;
        string prefix = "";
        string route = "direct";
        if (body.StartsWith("KBDARM|", StringComparison.Ordinal))
        {
            prefix = "KBDARM|"; route = "arm"; body = body[prefix.Length..];
        }
        else if (body.StartsWith("KBDPICO|", StringComparison.Ordinal))
        {
            prefix = "KBDPICO|"; route = "pico"; body = body[prefix.Length..];
        }

        if (body.StartsWith("KDOWN|", StringComparison.Ordinal)
            && int.TryParse(body["KDOWN|".Length..], out var downVk))
        {
            string key = route + ":" + downVk;
            lock (_heldKeyboardLock)
            {
                if (!_heldKeyboardKeys.Add(key))
                {
                    guardedCmd = null;
                    guardLog = $"keyboard guard: duplicate {body} suppressed ({route})";
                }
            }
            if (guardedCmd is not null) guardedCmd = prefix + body;
            return true;
        }

        if (body.StartsWith("KUP|", StringComparison.Ordinal)
            && int.TryParse(body["KUP|".Length..], out var upVk))
        {
            lock (_heldKeyboardLock) _heldKeyboardKeys.Remove(route + ":" + upVk);
            guardedCmd = prefix + body;
            return true;
        }

        return false;
    }

    private async Task ReleaseHeldKeyboardKeysAsync()
    {
        List<string> held;
        lock (_heldKeyboardLock)
        {
            held = _heldKeyboardKeys.ToList();
            _heldKeyboardKeys.Clear();
        }

        foreach (var key in held)
        {
            int split = key.IndexOf(':');
            if (split <= 0 || !int.TryParse(key[(split + 1)..], out var vk)) continue;
            string route = key[..split];
            string prefix = route == "arm" ? "KBDARM|" : route == "pico" ? "KBDPICO|" : "";
            try
            {
                await Send(prefix + $"KUP|{vk}", CancellationToken.None, quiet: true);
                _log($"keyboard guard: released held key {vk} ({route})");
            }
            catch (Exception ex)
            {
                _log($"keyboard guard: failed to release held key {vk} ({route}): {ex.Message}");
            }
        }
    }

"""
    if s.count(helper_anchor) != 1:
        raise SystemExit("RunEngine helper anchor mismatch")
    s = s.replace(helper_anchor, helper + helper_anchor, 1)

required = ["_heldKeyboardKeys", "TryHandleKeyboardStateGuard", "ReleaseHeldKeyboardKeysAsync"]
if not all(marker in s for marker in required):
    raise SystemExit("RunEngine keyboard guard postcondition failed")
PATH.write_text(s, encoding="utf-8", newline="\n")
