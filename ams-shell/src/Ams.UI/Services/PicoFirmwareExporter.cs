using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// v0.9.39 - per-system Pico output. Builds a CircuitPython bundle (code.py + boot.py +
/// pico-calibration.json + README-FLASH.md) out of the "Wait For Light" steps of the open plan.
/// The lux ranges are machine specific (monitor, ambient light, sensor position), so the export
/// is meant to be run once on every PC and copied onto that PC's Pico.
/// Sensor: BH1750 (GY-302 / GY-30) on I2C0, SDA=GP20 / SCL=GP21, ADDR-&gt;GND =&gt; 0x23,
/// continuous H-resolution (0x10, ~120 ms/sample), lux = raw / 1.2.
/// </summary>
public static class PicoFirmwareExporter
{
    public const string BundleVersion = "0.9.58";   // UART arm moved to GP16/GP17 (wiring v6)

    /// <summary>One calibrated screen state taken from a Wait For Light step.</summary>
    public sealed record LightState(string Name, int LuxLow, int LuxHigh, int StableMs, int TimeoutMs, int Mode, int KeyVk, string KeyName, bool Armed);

    /// <summary>Walks the whole step tree and reads every waitForLight range from its board command.</summary>
    public static List<LightState> CollectStates(IEnumerable<StepNode> steps)
    {
        var acc = new List<LightState>();
        Walk(steps, acc);
        return acc;
    }

    private static void Walk(IEnumerable<StepNode>? steps, List<LightState> acc)
    {
        if (steps is null) return;
        foreach (var s in steps)
        {
            if (s.Type == "waitForLight")
            {
                var cmd = StepDefinitions.GetCommands(s).FirstOrDefault() ?? "";
                var parts = cmd.Split('|');
                var args = parts.Length > 1 ? parts[1].Split(',') : Array.Empty<string>();
                bool armed = cmd.StartsWith("TRGLUX", StringComparison.Ordinal);
                acc.Add(new LightState(
                    string.IsNullOrWhiteSpace(s.Name) ? "light" + (acc.Count + 1) : s.Name,
                    Arg(args, 0, 0), Arg(args, 1, 0), Arg(args, 2, 2000), Arg(args, 3, 20000),
                    Arg(args, 4, 0), armed ? Arg(args, 5, 69) : 0,
                    PropEx.GetString(s.Props, "key", "E"), armed));
            }
            Walk(s.Children, acc);
        }
    }

    private static int Arg(string[] a, int i, int dflt)
        => a.Length > i && int.TryParse(a[i], NumberStyles.Integer, CultureInfo.InvariantCulture, out int v) ? v : dflt;

    private static string Escape(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");

    /// <summary>The per-system calibration file the firmware reads at boot.</summary>
    public static string BuildCalibrationJson(IReadOnlyList<LightState> states, string machine)
    {
        var sb = new StringBuilder();
        sb.AppendLine("{");
        sb.AppendLine("  \"generator\": \"Classroom Studio v" + BundleVersion + "\",");
        sb.AppendLine("  \"system\": \"" + Escape(machine) + "\",");
        sb.AppendLine("  \"generatedUtc\": \"" + DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + "\",");
        sb.AppendLine("  \"sensor\": { \"chip\": \"BH1750\", \"board\": \"GY-302/GY-30\", \"i2c\": \"I2C0 SDA=GP20 SCL=GP21\", \"addr\": 35 },");
        sb.AppendLine("  \"states\": [");
        for (int i = 0; i < states.Count; i++)
        {
            var st = states[i];
            sb.Append("    { \"name\": \"" + Escape(st.Name) + "\", \"luxLow\": " + st.LuxLow
                + ", \"luxHigh\": " + st.LuxHigh + ", \"stableMs\": " + st.StableMs
                + ", \"timeoutMs\": " + st.TimeoutMs + ", \"mode\": " + st.Mode
                + ", \"keyVk\": " + st.KeyVk + ", \"key\": \"" + Escape(st.KeyName)
                + "\", \"armed\": " + (st.Armed ? "true" : "false") + " }");
            sb.AppendLine(i < states.Count - 1 ? "," : "");
        }
        sb.AppendLine("  ]");
        sb.AppendLine("}");
        return sb.ToString();
    }

    /// <summary>code.py for this system (the placeholders are filled from the current plan).</summary>
    public static string BuildCodePy(IReadOnlyList<LightState> states, string machine,
        string loopMode = "forever", int loopCount = 0, int loopSeconds = 0, bool keyboardOnArm = false)
        => CodeTemplate
            .Replace("__MACHINE__", machine)
            .Replace("__GENERATED__", DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture))
            .Replace("__VERSION__", BundleVersion)
            .Replace("__STATE_COUNT__", states.Count.ToString(CultureInfo.InvariantCulture))
            .Replace("__LOOP_MODE__", loopMode)                                                    // v0.9.44
            .Replace("__LOOP_COUNT__", loopCount.ToString(CultureInfo.InvariantCulture))           // v0.9.44
            .Replace("__LOOP_SECONDS__", loopSeconds.ToString(CultureInfo.InvariantCulture))       // v0.9.44
            .Replace("__KBD_ON_ARM__", keyboardOnArm ? "True" : "False");                          // v0.9.44

    /// <summary>boot.py: enables the second USB serial so HID and the command channel coexist.</summary>
    public static string BuildBootPy() => BootTemplate;

    private const string BootTemplate = """
        # Classroom Studio - Pico boot configuration (CircuitPython)
        # Enables the second USB serial (data) so the app / bridge.py can send
        # WLUX / TRGLUX / LCAL commands while the HID keyboard stays available.
        import usb_cdc

        usb_cdc.enable(console=True, data=True)
        """;

    private const string CodeTemplate = """
        # Classroom Studio v__VERSION__ - Raspberry Pi Pico light-sensor firmware (CircuitPython)
        # System: __MACHINE__   generated: __GENERATED__   calibrated states: __STATE_COUNT__
        # Sensor: BH1750 (GY-302 / GY-30) on I2C0 - SDA=GP20, SCL=GP21, ADDR->GND => 0x23
        # Board roles (v0.9.39): the Pico is the executive brain - keyboard (USB HID) + light sensor.
        # Mouse and the sound sensor belong to the Arduino Pro Micro, which the Pico drives as its
        # arm over UART0: GP16 = TX -> Pro Micro RX, GP17 = RX <- Pro Micro TX, common GND, 115200 8N1.
        # v0.9.56 - moved from GP0/GP1 to GP16 (pin 21) / GP17 (pin 22) to match wiring v6 (BSS138 LV1/LV2).
        # v0.9.58 - keypad buttons: BTN1=GP2 (Num Lock = Run/Stop), BTN2=GP3 (Scroll Lock = Pause/Resume)
        # Copy code.py + boot.py + pico-calibration.json onto CIRCUITPY and put the
        # adafruit_hid package into /lib. Full instructions: README-FLASH.md

        import time
        import random
        import json
        import board
        import busio
        import usb_cdc
        import usb_hid
        from adafruit_hid.keyboard import Keyboard
        from adafruit_hid.keycode import Keycode

        ADDR = 0x23
        POWER_ON = 0x01
        RESET = 0x07
        CONT_HIRES = 0x10   # 1 lux, ~120 ms per sample (max 180 ms)
        CONT_LORES = 0x13   # 4 lux, ~16 ms per sample

        # v0.9.44 - Play Options baked at export time: how often the armed standalone states run.
        LOOP_MODE = "__LOOP_MODE__"      # once | times | timed | forever
        LOOP_COUNT = __LOOP_COUNT__      # passes for "times"
        LOOP_SECONDS = __LOOP_SECONDS__  # seconds for "timed"

        # v0.9.44 - Options: when set, the Pro Micro arm executes the keyboard instead of this Pico.
        KBD_ON_ARM = __KBD_ON_ARM__

        SPECIAL_VK = {
            0x0D: Keycode.ENTER, 0x1B: Keycode.ESCAPE, 0x20: Keycode.SPACE, 0x09: Keycode.TAB,
            0x08: Keycode.BACKSPACE, 0x25: Keycode.LEFT_ARROW, 0x27: Keycode.RIGHT_ARROW,
            0x26: Keycode.UP_ARROW, 0x28: Keycode.DOWN_ARROW,
        }
        # v0.9.44 - modifiers too, so KCOMBO shortcuts (Ctrl/Shift/Alt/Win + key) work on the Pico
        MOD_VK = {
            0xA0: Keycode.LEFT_SHIFT, 0xA1: Keycode.RIGHT_SHIFT,
            0xA2: Keycode.LEFT_CONTROL, 0xA3: Keycode.RIGHT_CONTROL,
            0xA4: Keycode.LEFT_ALT, 0xA5: Keycode.RIGHT_ALT,
            0x5B: Keycode.LEFT_GUI, 0x5C: Keycode.RIGHT_GUI,
        }
        DIGITS = ("ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE")


        def keycode_for_vk(vk):
            if 0x41 <= vk <= 0x5A:
                return getattr(Keycode, chr(vk))
            if 0x30 <= vk <= 0x39:
                return getattr(Keycode, DIGITS[vk - 0x30])
            if 0x70 <= vk <= 0x7B:
                return getattr(Keycode, "F" + str(vk - 0x6F))
            return SPECIAL_VK.get(vk, MOD_VK.get(vk, Keycode.E))   # v0.9.44 - modifiers included


        class Bh1750:
            def __init__(self, i2c, mode=CONT_HIRES):
                self._i2c = i2c
                self._buf = bytearray(2)
                self.mode = None
                self._cmd(POWER_ON)
                self._cmd(RESET)
                self.set_mode(mode)

            def _cmd(self, value):
                while not self._i2c.try_lock():
                    pass
                try:
                    self._i2c.writeto(ADDR, bytes([value]))
                finally:
                    self._i2c.unlock()

            def set_mode(self, mode):
                if mode == self.mode:
                    return
                self.mode = mode
                self._cmd(mode)          # sent once per mode change, never per sample
                time.sleep(0.2 if mode == CONT_HIRES else 0.05)

            def lux(self):
                while not self._i2c.try_lock():
                    pass
                try:
                    self._i2c.readfrom_into(ADDR, self._buf)
                finally:
                    self._i2c.unlock()
                raw = (self._buf[0] << 8) | self._buf[1]
                return raw / 1.2         # datasheet conversion


        def median(values):
            ordered = sorted(values)
            return ordered[len(ordered) // 2]


        def load_states():
            try:
                with open("/pico-calibration.json", "r") as fh:
                    return json.load(fh).get("states", [])
            except Exception:
                return []


        i2c = busio.I2C(board.GP21, board.GP20)   # SCL, SDA
        sensor = Bh1750(i2c)
        kbd = Keyboard(usb_hid.devices)
        serial = usb_cdc.data if usb_cdc.data is not None else usb_cdc.console
        states = load_states()
        window = []

        # Commands that are not the brain's own job: forwarded verbatim to the Pro Micro arm.
        ARM_PREFIXES = ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP", "SETRES", "WSND", "TRGSND", "SCAL")
        # v0.9.44 - keyboard commands: typed locally here, or forwarded to the arm when Options says so
        KBD_PREFIXES = ("KTEXT", "KCOMBO", "KDOWN", "KUP")
        try:
            arm = busio.UART(board.GP16, board.GP17, baudrate=115200, timeout=0.2)
        except Exception:
            arm = None
        # v0.9.58 — hardware keypad (BTN1=GP2, BTN2=GP3, active-low to GND, 40ms debounce)
        try:
            import digitalio
            btn1 = digitalio.DigitalInOut(board.GP2)
            btn1.direction = digitalio.Direction.INPUT
            btn1.pull = digitalio.Pull.UP
            btn2 = digitalio.DigitalInOut(board.GP3)
            btn2.direction = digitalio.Direction.INPUT
            btn2.pull = digitalio.Pull.UP
            _last_btn1 = True
            _last_btn2 = True
        except Exception:
            btn1 = btn2 = None
            _last_btn1 = _last_btn2 = True


        def forward_to_arm(line, timeout_s):
            if arm is None:
                return "ERR|NOARM|" + line.split("|")[0]
            arm.write((line + "\n").encode("utf-8"))
            end = time.monotonic() + timeout_s
            pending = ""
            while time.monotonic() < end:
                chunk = arm.read(64)
                if chunk:
                    pending += chunk.decode("utf-8")
                    if "\n" in pending:
                        return pending.split("\n")[0].strip()
                time.sleep(0.005)
            return "ERR|TIMEOUT|" + line.split("|")[0]


        def sample():
            window.append(sensor.lux())
            if len(window) > 5:
                window.pop(0)
            return median(window)


        def press(vk, hold_ms):
            code = keycode_for_vk(vk)
            kbd.press(code)
            time.sleep(max(10, hold_ms) / 1000)
            kbd.release(code)


        def wait_range(lo, hi, stable_ms, timeout_ms, mode):
            sensor.set_mode(CONT_LORES if mode == 1 else CONT_HIRES)
            deadline = time.monotonic() + timeout_ms / 1000
            inside_since = None
            while time.monotonic() < deadline:
                value = sample()
                if lo <= value <= hi:
                    if inside_since is None:
                        inside_since = time.monotonic()
                    elif (time.monotonic() - inside_since) * 1000 >= stable_ms:
                        return value      # stabilized inside the range for n seconds
                else:
                    inside_since = None
                time.sleep(0.02)
            return None


        def ints(fields, count, default=0):
            out = []
            for i in range(count):
                try:
                    out.append(int(fields[i]))
                except Exception:
                    out.append(default)
            return out


        def handle_keyboard(line, head):
            # v0.9.44 - local keyboard execution (when the arm does NOT own the keyboard)
            if head == "KDOWN":
                kbd.press(keycode_for_vk(int(line.split("|")[1])))
                return "OK|KDOWN"
            if head == "KUP":
                kbd.release(keycode_for_vk(int(line.split("|")[1])))
                return "OK|KUP"
            if head == "KCOMBO":
                # KCOMBO|vk+vk+...[,hmin,hmax] - press in order, random hold, release in reverse
                body = line.split("|", 1)[1]
                hold = 0.0
                if "," in body:
                    body, holdpart = body.split(",", 1)
                    hp = holdpart.split(",")
                    try:
                        h0 = int(hp[0])
                        h1 = int(hp[1]) if len(hp) > 1 else h0
                        hold = random.uniform(max(0, h0), max(0, h1)) if max(h0, h1) > 0 else 0.0
                    except Exception:
                        hold = 0.0
                codes = [keycode_for_vk(int(v)) for v in body.split("+") if v]
                for c in codes:
                    kbd.press(c)
                time.sleep(max(10.0, hold) / 1000)
                for c in reversed(codes):
                    kbd.release(c)
                return "OK|KCOMBO"
            if head == "KTEXT":
                # KTEXT|hmin,hmax,text - ASCII only (the firmware 1.6 rule), per-key random delay
                parts = line.split("|", 1)[1].split(",", 2)
                try:
                    hmin, hmax = int(parts[0]), int(parts[1])
                except Exception:
                    hmin, hmax = 0, 0
                txt = parts[2] if len(parts) > 2 else ""
                for ch in txt:
                    if ord(ch) < 32 or ord(ch) > 126:
                        return "ERR|ASCII|KTEXT"
                for ch in txt:
                    kbd.write(ch)
                    if hmax > 0:
                        time.sleep(random.uniform(max(0, hmin), hmax) / 1000)
                return "OK|KTEXT"
            return "ERR|UNKNOWN|" + head


        def handle(line):
            if line == "PING":
                return "OK|PONG|pico-light __VERSION__|role=brain+keyboard+light|arm=promicro"
            if line.startswith("LCAL|"):
                ms = ints(line.split("|")[1].split(","), 1, 2000)[0] or 2000
                sensor.set_mode(CONT_HIRES)
                end = time.monotonic() + ms / 1000
                readings = []
                while time.monotonic() < end:
                    readings.append(sensor.lux())
                    time.sleep(0.02)
                if not readings:
                    readings = [sensor.lux()]
                lo = int(min(readings))
                hi = int(max(readings))
                avg = int(sum(readings) / len(readings))
                return "OK|LCAL|min=%d|max=%d|avg=%d" % (lo, hi, avg)
            if line.startswith("WLUX|"):
                a = ints(line.split("|")[1].split(","), 5)
                got = wait_range(a[0], a[1], a[2] or 2000, a[3] or 20000, a[4])
                if got is None:
                    return "ERR|TIMEOUT|WLUX"
                return "OK|WLUX|lux=%d" % int(got)
            if line.startswith("TRGLUX|"):
                a = ints(line.split("|")[1].split(","), 10)
                got = wait_range(a[0], a[1], a[2] or 2000, a[3] or 20000, a[4])
                if got is None:
                    return "ERR|TIMEOUT|TRGLUX"
                time.sleep(max(0, a[6]) / 1000)   # reaction delay (reactMin)
                press(a[5], a[8] or 40)           # board-side keypress (holdMin)
                return "EVT|TRGLUX|lux=%d|vk=%d" % (int(got), a[5])
            if line in ("HALT", "BYE"):
                if arm is not None:
                    forward_to_arm(line, 2)          # stop the arm too
                return "OK|" + line
            # v0.9.46 - a keyboard step may override the global Options rule for THIS command.
            # The envelope is consumed by the Pico brain and never forwarded to firmware 1.6.
            forced_keyboard_arm = None
            if line.startswith("KBDPICO|"):
                forced_keyboard_arm = False
                line = line.split("|", 1)[1]
            elif line.startswith("KBDARM|"):
                forced_keyboard_arm = True
                line = line.split("|", 1)[1]
            head = line.split("|")[0]
            if head in KBD_PREFIXES:
                keyboard_on_arm = KBD_ON_ARM if forced_keyboard_arm is None else forced_keyboard_arm
                if not keyboard_on_arm:
                    return handle_keyboard(line, head)
                tmo = 5
                if head == "KTEXT":
                    try:
                        _p = line.split("|", 1)[1].split(",", 2)
                        tmo = max(5.0, float(_p[1]) * len(_p[2]) / 1000 + 5)
                    except Exception:
                        tmo = 30
                return forward_to_arm(line, tmo)
            if head in ARM_PREFIXES:
                # brain -> arm: mouse and sound always belong to the Pro Micro
                tmo = 30 if head in ("WSND", "TRGSND", "SCAL") else 5
                return forward_to_arm(line, tmo)
            return "ERR|UNKNOWN|" + line


        def standalone_pass():
            # No host command pending: run the armed states of this system in order.
            for st in states:
                if not st.get("armed"):
                    continue
                got = wait_range(st.get("luxLow", 0), st.get("luxHigh", 0),
                                 st.get("stableMs", 2000), st.get("timeoutMs", 20000),
                                 st.get("mode", 0))
                if got is not None:
                    press(st.get("keyVk", 69), 40)


        def loop_due():
            # v0.9.44 - Play Options baked at export: how often the armed states run standalone
            if LOOP_MODE == "once":
                return passes == 0
            if LOOP_MODE == "times":
                return passes < LOOP_COUNT
            if LOOP_MODE == "timed":
                return time.monotonic() - started < LOOP_SECONDS
            return True                      # forever - the pre-v0.9.44 behavior


        buffer = ""
        passes = 0
        started = time.monotonic()
        while True:
            if serial is not None and serial.in_waiting:
                buffer += serial.read(serial.in_waiting).decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    serial.write((handle(line) + "\n").encode("utf-8"))
            else:
                if states and loop_due():
                    standalone_pass()
                    passes += 1
                # v0.9.58 — hardware keypad poll (BTN1=GP2→NumLock, BTN2=GP3→ScrollLock, 40ms debounce)
                if btn1 is not None:
                    b1 = not btn1.value
                    b2 = not btn2.value
                    if b1 and not _last_btn1:
                        kbd.send(Keycode.NUM_LOCK)
                    if b2 and not _last_btn2:
                        kbd.send(Keycode.SCROLL_LOCK)
                    _last_btn1 = b1
                    _last_btn2 = b2
                time.sleep(0.05)
        """;

    /// <summary>Per-system flashing + calibration instructions (Persian, like the other docs).</summary>
    public static string BuildReadme(IReadOnlyList<LightState> states, string machine,
        string loopMode = "forever", int loopCount = 0, int loopSeconds = 0, bool keyboardOnArm = false)   // v0.9.44
    {
        var sb = new StringBuilder();
        sb.AppendLine("# Pico light sensor - " + machine);
        sb.AppendLine();
        sb.AppendLine("Classroom Studio v" + BundleVersion + " - " + DateTime.Now.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture));
        sb.AppendLine();
        sb.AppendLine("Play Options baked in (v0.9.44): loop=" + loopMode + (loopMode == "times" ? " x" + loopCount : loopMode == "timed" ? " " + loopSeconds + "s" : "") + " | keyboard=" + (keyboardOnArm ? "Pro Micro (arm)" : "Pico (brain)"));   // v0.9.44
        sb.AppendLine();
        sb.AppendLine("\u0627\u06cc\u0646 \u062e\u0631\u0648\u062c\u06cc \u0645\u062e\u0635\u0648\u0635 \u0647\u0645\u06cc\u0646 \u0633\u06cc\u0633\u062a\u0645 \u0627\u0633\u062a\u061b \u0645\u0642\u062f\u0627\u0631 \u0644\u0648\u06a9\u0633 \u062f\u0631 \u0647\u0631 \u0645\u0627\u0646\u06cc\u062a\u0648\u0631 \u0648 \u0647\u0631 \u0627\u062a\u0627\u0642 \u0645\u062a\u0641\u0627\u0648\u062a \u0627\u0633\u062a\u060c \u067e\u0633 \u062f\u0631 \u0647\u0631 \u0633\u06cc\u0633\u062a\u0645 \u06cc\u06a9\u200c\u0628\u0627\u0631 \u0627\u06cc\u0646 \u062e\u0631\u0648\u062c\u06cc \u0631\u0627 \u0628\u0633\u0627\u0632 \u0648 \u0631\u0648\u06cc \u0628\u0631\u062f \u0628\u0631\u06cc\u0632.");
        sb.AppendLine();
        sb.AppendLine("## \u0641\u0627\u06cc\u0644\u200c\u0647\u0627");
        sb.AppendLine();
        sb.AppendLine("- `code.py` - \u0641\u0631\u0645\u200c\u0648\u0631 \u0627\u0635\u0644\u06cc (CircuitPython)");
        sb.AppendLine("- `boot.py` - \u0641\u0639\u0627\u0644 \u06a9\u0631\u062f\u0646 \u0633\u0631\u06cc\u0627\u0644 \u062f\u0648\u0645 \u06a9\u0646\u0627\u0631 \u06a9\u06cc\u0628\u0648\u0631\u062f HID");
        sb.AppendLine("- `pico-calibration.json` - \u0628\u0627\u0632\u0647\u200c\u0647\u0627\u06cc \u0644\u0648\u06a9\u0633 \u0647\u0645\u06cc\u0646 \u0633\u06cc\u0633\u062a\u0645");
        sb.AppendLine();
        sb.AppendLine("## \u0645\u0631\u0627\u062d\u0644 \u0631\u06cc\u062e\u062a\u0646 \u0631\u0648\u06cc \u0628\u0631\u062f");
        sb.AppendLine();
        sb.AppendLine("1. \u062f\u06a9\u0645\u0647 BOOTSEL \u0631\u0627 \u0646\u06af\u0647 \u062f\u0627\u0631 \u0648 \u067e\u06cc\u06a9\u0648 \u0631\u0627 \u0628\u0647 USB \u0628\u0632\u0646\u061b \u062f\u0631\u0627\u06cc\u0648 RPI-RP2 \u0628\u0627\u0644\u0627 \u0645\u06cc\u200c\u0622\u06cc\u062f.");
        sb.AppendLine("2. \u0641\u0627\u06cc\u0644 UF2 \u0645\u0631\u0628\u0648\u0637 \u0628\u0647 CircuitPython 9.x \u0631\u0627 \u062f\u0631 \u0627\u06cc\u0646 \u062f\u0631\u0627\u06cc\u0648 \u06a9\u067e\u06cc \u06a9\u0646 (\u0641\u0642\u0637 \u0628\u0627\u0631 \u0627\u0648\u0644 \u0628\u0631\u0627\u06cc \u0647\u0631 \u0628\u0631\u062f).");
        sb.AppendLine("3. \u0628\u0639\u062f \u0627\u0632 \u0631\u06cc\u0633\u062a\u060c \u062f\u0631\u0627\u06cc\u0648 CIRCUITPY \u0645\u06cc\u200c\u0622\u06cc\u062f: \u0647\u0631 \u0633\u0647 \u0641\u0627\u06cc\u0644 \u0628\u0627\u0644\u0627 \u0631\u0627 \u062f\u0631 \u0631\u06cc\u0634\u0647\u200c\u06cc \u0622\u0646 \u0628\u0631\u06cc\u0632.");
        sb.AppendLine("4. \u067e\u0648\u0634\u0647\u200c\u06cc `adafruit_hid` \u0631\u0627 \u0627\u0632 CircuitPython Library Bundle \u062f\u0631 `CIRCUITPY/lib` \u0628\u06af\u0630\u0627\u0631.");
        sb.AppendLine("5. \u0633\u06cc\u0645\u200c\u06a9\u0634\u06cc GY-302/GY-30: `VCC -> 3V3 (pin 36)` \u060c `GND -> GND (pin 38)` \u060c `SDA -> GP20 (pin 26)` \u060c `SCL -> GP21 (pin 27)` \u060c `ADDR -> GND` (\u0622\u062f\u0631\u0633 0x23).");
        sb.AppendLine("6. \u0633\u0646\u0633\u0648\u0631 \u0631\u0627 \u0628\u0627 \u0647\u0648\u062f \u062a\u0627\u0631\u06cc\u06a9 \u0631\u0648\u06cc \u0646\u0627\u062d\u06cc\u0647\u200c\u06cc \u0645\u0648\u0631\u062f\u0646\u0637\u0631 \u0635\u0641\u062d\u0647 \u062b\u0627\u0628\u062a \u06a9\u0646 (\u0646\u0648\u0631 \u0645\u062d\u06cc\u0637 \u0646\u0628\u0627\u06cc\u062f \u0628\u0631\u0633\u062f).");
        sb.AppendLine("7. \u062f\u0631 \u0628\u0631\u0646\u0627\u0645\u0647: Insert -> Wait For Light\u060c \u0647\u0645\u0627\u0646 \u0648\u0636\u0639\u06cc\u062a \u0631\u0627 \u0631\u0648\u06cc \u0635\u0641\u062d\u0647 \u0628\u06cc\u0627\u0648\u0631 \u0648 \u062f\u06a9\u0645\u0647\u200c\u06cc Calibrate \u0631\u0627 \u0628\u0632\u0646 (LCAL)\u061b \u062a\u0644\u0648\u0631\u0627\u0646\u0633 \u0631\u0627 \u062f\u0633\u062a\u200c\u06a9\u0645 \u06f5\u06f0 \u0644\u0648\u06a9\u0633 \u0628\u06af\u0630\u0627\u0631.");
        sb.AppendLine("8. \u0628\u06cc\u0646 \u062f\u0648 \u0648\u0636\u0639\u06cc\u062a \u0645\u062a\u0641\u0627\u0648\u062a \u062d\u062f\u0627\u0642\u0644 \u06f5\u06f0 \u0644\u0648\u06a9\u0633 \u0641\u0627\u0635\u0644\u0647\u200c\u06cc \u062e\u0627\u0644\u06cc (dead zone) \u0644\u0627\u0632\u0645 \u0627\u0633\u062a.");
        sb.AppendLine();
        sb.AppendLine("## \u0628\u0627\u0632\u0647\u200c\u0647\u0627\u06cc \u0627\u06cc\u0646 \u0646\u0642\u0634\u0647");
        sb.AppendLine();
        if (states.Count == 0)
        {
            sb.AppendLine("\u0647\u06cc\u0686 \u06af\u0627\u0645 Wait For Light \u062f\u0631 \u0627\u06cc\u0646 \u0646\u0642\u0634\u0647 \u0646\u06cc\u0633\u062a - \u0641\u0631\u0645\u200c\u0648\u0631 \u0641\u0642\u0637 \u0628\u0647 \u0641\u0631\u0645\u0627\u0646\u200c\u0647\u0627\u06cc \u0628\u0631\u0646\u0627\u0645\u0647 (WLUX/LCAL) \u067e\u0627\u0633\u062e \u0645\u06cc\u200c\u062f\u0647\u062f.");
        }
        else
        {
            sb.AppendLine("| state | lux range | stable | timeout | mode | key | armed |");
            sb.AppendLine("|---|---|---|---|---|---|---|");
            foreach (var st in states)
                sb.AppendLine("| " + st.Name + " | " + st.LuxLow + "-" + st.LuxHigh + " | " + (st.StableMs / 1000.0).ToString("0.#", CultureInfo.InvariantCulture)
                    + "s | " + st.TimeoutMs + "ms | " + (st.Mode == 1 ? "lowres" : "hires") + " | " + st.KeyName + " | " + (st.Armed ? "yes" : "no") + " |");
        }
        sb.AppendLine();
        sb.AppendLine("## \u067e\u0631\u0648\u062a\u06a9\u0644 \u0633\u0631\u06cc\u0627\u0644");
        sb.AppendLine();
        sb.AppendLine("- `PING` -> `OK|PONG|pico-light " + BundleVersion + "`");
        sb.AppendLine("- `LCAL|ms` -> `OK|LCAL|min=..|max=..|avg=..` (\u062f\u06a9\u0645\u0647\u200c\u06cc Calibrate \u0647\u0645\u06cc\u0646 \u0631\u0627 \u0645\u06cc\u200c\u0632\u0646\u062f)");
        sb.AppendLine("- `WLUX|luxLow,luxHigh,stableMs,timeoutMs,mode` -> `OK|WLUX|lux=..` \u06cc\u0627 `ERR|TIMEOUT|WLUX`");
        sb.AppendLine("- `TRGLUX|luxLow,luxHigh,stableMs,timeoutMs,mode,vk,reactMin,reactMax,holdMin,holdMax` -> `EVT|TRGLUX|...` (\u06a9\u0644\u06cc\u062f \u0631\u0627 \u062e\u0648\u062f \u0628\u0631\u062f \u0645\u06cc\u200c\u0632\u0646\u062f)");
        sb.AppendLine("- `HALT` / `BYE` -> `OK|...`");
        return sb.ToString();
    }

    /// <summary>Writes the whole bundle next to <paramref name="codePyPath"/> and returns the written paths.</summary>
    public static IReadOnlyList<string> Export(string codePyPath, IEnumerable<StepNode> steps, string machine,
        string loopMode = "forever", int loopCount = 0, int loopSeconds = 0, bool keyboardOnArm = false)   // v0.9.44 — Play Options + keyboard board
    {
        var dir = Path.GetDirectoryName(codePyPath);
        if (string.IsNullOrEmpty(dir)) throw new IOException("no target folder for the Pico bundle");
        var states = CollectStates(steps);
        var written = new List<string>();
        void Put(string name, string text)
        {
            var p = Path.Combine(dir, name);
            File.WriteAllText(p, text);
            written.Add(p);
        }
        Put(string.IsNullOrWhiteSpace(Path.GetFileName(codePyPath)) ? "code.py" : Path.GetFileName(codePyPath), BuildCodePy(states, machine, loopMode, loopCount, loopSeconds, keyboardOnArm));   // v0.9.44
        Put("boot.py", BuildBootPy());
        Put("pico-calibration.json", BuildCalibrationJson(states, machine));
        Put("README-FLASH.md", BuildReadme(states, machine, loopMode, loopCount, loopSeconds, keyboardOnArm));   // v0.9.44
        return written;
    }
}
