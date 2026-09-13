from pathlib import Path
import re


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def sub(path, pattern, replacement, flags=0, expected=1):
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, flags=flags)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected}, found {count}: {pattern[:100]!r}")
    write(path, updated)


bridge = "ams-shell/bridge/bridge.py"
sub(bridge, r"\n\ndef open_link\(port\):", '''

def _mclick_timeout(cmd, default):
    """Allow completion of count x randomized physical holds."""
    if not cmd.startswith("MCLICK|"):
        return default
    try:
        fields = cmd.split("|", 1)[1].split(",")
        count = max(1, int(fields[1])) if len(fields) > 1 else 1
        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45
        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin
        return max(default, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)
    except Exception:
        return default


def _command_timeout(cmd, default):
    return max(_ktext_timeout(cmd, default), _mclick_timeout(cmd, default))


def open_link(port):''')
sub(bridge, r'timeout=_ktext_timeout\(cmd, req\.get\("timeout", 5\.0\)\)', 'timeout=_command_timeout(cmd, req.get("timeout", 5.0))')


def patch_pico(path):
    sub(path, r'(?m)^(?P<i>[ \t]*)MOUSE_PREFIXES = \("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP"\)$', r'\g<i>FAST_MOUSE_PREFIXES = ("MMOVE", "MWHEEL", "MDOWN", "MUP")')
    sub(path, r'parts\[1\] in MOUSE_PREFIXES', 'parts[1] in FAST_MOUSE_PREFIXES')
    sub(path, r'(?m)^(?P<i>[ \t]*)_arm_buf = bytearray\(\)$', r'\g<i>_arm_buf = bytearray()\n\g<i>_last_hostusb_event = [None]  # forward identical HOSTUSB heartbeats once')
    sub(path,
        r'(?m)^(?P<i>[ \t]*)if line\.startswith\("EVT\|"\):\n(?P=i)    _serial_write_line\(line\)[^\n]*\n(?P=i)    continue$',
        r'''\g<i>if line.startswith("EVT|"):
\g<i>    if line.startswith("EVT|HOSTUSB|"):
\g<i>        if line == _last_hostusb_event[0]:
\g<i>            continue
\g<i>        _last_hostusb_event[0] = line
\g<i>    _serial_write_line(line)              # changed events reach the PC once
\g<i>    continue''')
    helper = '''def _mclick_timeout(line):
    """Physical-completion timeout for all randomized holds and inter-click gaps."""
    try:
        fields = line.split("|", 1)[1].split(",")
        count = max(1, int(fields[1])) if len(fields) > 1 else 1
        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45
        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin
        return max(5.0, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)
    except Exception:
        return 5.0


'''
    text = read(path)
    match = re.search(r'(?m)^(?P<i>[ \t]*)def sample\(\):$', text)
    if match is None:
        raise SystemExit(f"{path}: sample anchor missing")
    indent = match.group('i')
    indented_helper = ''.join(indent + line if line else line for line in helper.splitlines(keepends=True))
    text = text[:match.start()] + indented_helper + text[match.start():]
    write(path, text)
    sub(path,
        r'(?m)^(?P<i>[ \t]*)if head in MOUSE_PREFIXES:\n(?P=i)    return forward_fast\(line\)\n(?P=i)if head in ARM_PREFIXES:',
        r'''\g<i>if head == "MCLICK":
\g<i>    return forward_to_arm(line, _mclick_timeout(line))
\g<i>if head in FAST_MOUSE_PREFIXES:
\g<i>    return forward_fast(line)
\g<i>if head in ARM_PREFIXES:''')


patch_pico("firmware/pico-light-0.9.60-template.py")
exporter = "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
patch_pico(exporter)
sub(exporter, r'(?m)^(?P<i>[ \t]*)forward_fast\(line\)\n\n(?P<j>[ \t]*)def ktext', r'\g<i>return self._ok(forward_to_arm(line, _mclick_timeout(line)), "MCLICK")\n\n\g<j>def ktext')
sub(exporter, r'public const string BundleVersion = "0\.9\.64f";', 'public const string BundleVersion = "0.9.64g";')

arm = "firmware/arm26/ams_board26.ino"
sub(arm, r'// ================= command handler =================\n', '''// Keep long physical clicks HALT-abortable instead of blocking in delay(hold).
static bool wait_mouse_hold_or_abort(uint16_t holdMs) {
  unsigned long started = millis();
  while (millis() - started < holdMs) {
    if (serial1_line_ready()) {
      if (!strncmp(g_line1, "HALT", 4)) {
        do_halt();
        send_line("ERR|ABORTED|MCLICK");
        return false;
      }
      reply_err("BUSY");
    }
    if (Serial.available() && read_line_blocking(4)) {
      static char pending[MAX_PT];
      if (decrypt_to(g_line, pending, MAX_PT) && !strncmp(pending, "HALT", 4)) {
        do_halt();
        send_line("ERR|ABORTED|MCLICK");
        return false;
      }
      reply_err("BUSY");
    }
    delay(2);
  }
  return true;
}

// ================= command handler =================
''')
sub(arm,
    r'SingleAbsoluteMouse\.press\(b\);\n(?P<i>[ \t]*)int hold = \(hmx > hmn && hmn > 0\) \? \(int\)random\(hmn, hmx \+ 1\) : 45;\n(?P=i)delay\(hold\);\n(?P=i)SingleAbsoluteMouse\.release\(b\);',
    r'''SingleAbsoluteMouse.press(b);
\g<i>int hold = (hmx > hmn && hmn > 0) ? (int)random(hmn, hmx + 1) : 45;
\g<i>if (!wait_mouse_hold_or_abort((uint16_t)hold)) return;
\g<i>SingleAbsoluteMouse.release(b);''')

Path("tests/MouseStopReliabilityTests.cs").write_text(r'''using System;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class MouseStopReliabilityTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var code = PicoFirmwareExporter.BuildCodePy(Array.Empty<PicoFirmwareExporter.LightState>(), "mouse-stop-test");
        if (!code.Contains("FAST_MOUSE_PREFIXES", StringComparison.Ordinal)
            || code.Contains("MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\"", StringComparison.Ordinal))
            throw new Exception("MCLICK is still fire-and-ack");
        if (!code.Contains("forward_to_arm(line, _mclick_timeout(line))", StringComparison.Ordinal))
            throw new Exception("MCLICK does not wait for physical release");
        if (!code.Contains("if line == _last_hostusb_event[0]", StringComparison.Ordinal))
            throw new Exception("HOSTUSB deduplication missing");
    }
}
''', encoding="utf-8")
print("mouse reliability patch v2 applied")
