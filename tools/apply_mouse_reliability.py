from pathlib import Path


def replace(path, old, new, expected=1):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != expected:
        raise SystemExit(f"{path}: expected {expected} matches, found {found}: {old[:80]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# Host bridge: a long MCLICK must wait for the physical Up, not hit the generic 5 s ceiling.
bridge = "ams-shell/bridge/bridge.py"
replace(
    bridge,
    "\n\ndef open_link(port):",
    '''\n\ndef _mclick_timeout(cmd, default):
    """Wait through the complete physical click. MCLICK may hold each click for hmax ms."""
    inner = cmd
    if not inner.startswith("MCLICK|"):
        return default
    try:
        fields = inner.split("|", 1)[1].split(",")
        count = max(1, int(fields[1])) if len(fields) > 1 else 1
        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45
        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin
        return max(default, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)
    except Exception:
        return default


def _command_timeout(cmd, default):
    return max(_ktext_timeout(cmd, default), _mclick_timeout(cmd, default))


def open_link(port):''')
replace(
    bridge,
    'reply = link.command(cmd, timeout=_ktext_timeout(cmd, req.get("timeout", 5.0)))',
    'reply = link.command(cmd, timeout=_command_timeout(cmd, req.get("timeout", 5.0)))')


# Shared transformations for the exported Pico firmware and the checked-in reference template.
def patch_pico(path, embedded=False):
    indent = "        " if embedded else ""
    replace(
        path,
        indent + 'MOUSE_PREFIXES = ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP")',
        indent + 'FAST_MOUSE_PREFIXES = ("MMOVE", "MWHEEL", "MDOWN", "MUP")')
    replace(path, 'parts[1] in MOUSE_PREFIXES', 'parts[1] in FAST_MOUSE_PREFIXES')
    replace(
        path,
        indent + '_arm_buf = bytearray()\n',
        indent + '_arm_buf = bytearray()\n' + indent + '_last_hostusb_event = [None]  # identical arm heartbeats are emitted to the PC once\n')
    replace(
        path,
        indent + '''if line.startswith("EVT|"):
''' + indent + '''    _serial_write_line(line)              # arm events reach the PC live
''' + indent + '''    continue''',
        indent + '''if line.startswith("EVT|"):
''' + indent + '''    if line.startswith("EVT|HOSTUSB|"):
''' + indent + '''        if line == _last_hostusb_event[0]:
''' + indent + '''            continue
''' + indent + '''        _last_hostusb_event[0] = line
''' + indent + '''    _serial_write_line(line)              # changed events reach the PC once
''' + indent + '''    continue''')
    helper = indent + '''def _mclick_timeout(line):
''' + indent + '''    """Physical completion timeout for count x randomized hold plus inter-click gaps."""
''' + indent + '''    try:
''' + indent + '''        fields = line.split("|", 1)[1].split(",")
''' + indent + '''        count = max(1, int(fields[1])) if len(fields) > 1 else 1
''' + indent + '''        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45
''' + indent + '''        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin
''' + indent + '''        return max(5.0, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)
''' + indent + '''    except Exception:
''' + indent + '''        return 5.0


'''
    replace(path, '\n\n' + indent + 'def sample():', '\n\n' + helper + indent + 'def sample():')
    replace(
        path,
        indent + '''if head in MOUSE_PREFIXES:
''' + indent + '''    return forward_fast(line)
''' + indent + '''if head in ARM_PREFIXES:''',
        indent + '''if head == "MCLICK":
''' + indent + '''    return forward_to_arm(line, _mclick_timeout(line))
''' + indent + '''if head in FAST_MOUSE_PREFIXES:
''' + indent + '''    return forward_fast(line)
''' + indent + '''if head in ARM_PREFIXES:''')


patch_pico("firmware/pico-light-0.9.60-template.py", embedded=False)
patch_pico("ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs", embedded=True)

# The portable plan context must also wait for click completion.
replace(
    "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs",
    '''                forward_fast(line)

            def ktext''',
    '''                return self._ok(forward_to_arm(line, _mclick_timeout(line)), "MCLICK")

            def ktext''')
replace(
    "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs",
    'public const string BundleVersion = "0.9.64f";',
    'public const string BundleVersion = "0.9.64g";')


# Arm firmware: make a long physical hold HALT-abortable in 2 ms slices.
arm = "firmware/arm26/ams_board26.ino"
replace(
    arm,
    "// ================= command handler =================\n",
    '''// A long MCLICK must remain HALT-abortable. The old delay(hold) blocked Serial1,
// so Stop could not release the button until the entire 3-4 second hold had elapsed.
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
replace(
    arm,
    '''      SingleAbsoluteMouse.press(b);
      int hold = (hmx > hmn && hmn > 0) ? (int)random(hmn, hmx + 1) : 45;
      delay(hold);
      SingleAbsoluteMouse.release(b);''',
    '''      SingleAbsoluteMouse.press(b);
      int hold = (hmx > hmn && hmn > 0) ? (int)random(hmn, hmx + 1) : 45;
      if (!wait_mouse_hold_or_abort((uint16_t)hold)) return;
      SingleAbsoluteMouse.release(b);''')


# Source-level regression runs automatically through the existing TestRunner project.
Path("tests/MouseStopReliabilityTests.cs").write_text(r'''using System;
using System.Runtime.CompilerServices;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class MouseStopReliabilityTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var code = PicoFirmwareExporter.BuildCodePy(
            Array.Empty<PicoFirmwareExporter.LightState>(), "mouse-stop-test");
        if (!code.Contains("FAST_MOUSE_PREFIXES", StringComparison.Ordinal)
            || code.Contains("MOUSE_PREFIXES = (\"MMOVE\", \"MCLICK\"", StringComparison.Ordinal))
            throw new Exception("MCLICK is still on the fire-and-ack path");
        if (!code.Contains("if head == \"MCLICK\":", StringComparison.Ordinal)
            || !code.Contains("forward_to_arm(line, _mclick_timeout(line))", StringComparison.Ordinal))
            throw new Exception("MCLICK does not wait for the physical release");
        if (!code.Contains("_last_hostusb_event = [None]", StringComparison.Ordinal)
            || !code.Contains("if line == _last_hostusb_event[0]", StringComparison.Ordinal))
            throw new Exception("HOSTUSB heartbeat deduplication is missing");
    }
}
''', encoding="utf-8")

print("mouse reliability patch applied")
