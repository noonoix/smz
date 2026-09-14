from pathlib import Path


def once(text, old, new, label):
    if old in text:
        if text.count(old) != 1:
            raise RuntimeError(f"{label}: expected one match, found {text.count(old)}")
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: anchor not found")


def patch_pico_body(text):
    text = text.replace("pico-light 0.9.64f", "pico-light 0.9.64h")
    text = text.replace("pico-light 0.9.64g", "pico-light 0.9.64h")
    text = once(text, 'MOUSE_PREFIXES = ("MMOVE", "MCLICK", "MWHEEL", "MDOWN", "MUP")', '# MCLICK waits for physical completion so an in-flight hold can be aborted.\nFAST_MOUSE_PREFIXES = ("MMOVE", "MWHEEL", "MDOWN", "MUP")', "fast mouse prefixes")
    text = once(text, "parts[1] in MOUSE_PREFIXES", "parts[1] in FAST_MOUSE_PREFIXES", "mouse ACK filter")

    helper = '''def _mclick_timeout(line):
    """Physical-completion timeout for randomized MCLICK holds."""
    try:
        fields = line.split("|", 1)[1].split(",")
        count = max(1, int(fields[1])) if len(fields) > 1 else 1
        hmin = max(0, int(fields[2])) if len(fields) > 2 else 45
        hmax = max(hmin, int(fields[3])) if len(fields) > 3 else hmin
        return max(5.0, 2.0 + (count * hmax + max(0, count - 1) * 140) / 1000.0)
    except Exception:
        return 5.0

'''
    if "def _mclick_timeout(line):" not in text:
        text = once(text, "def sample():", helper + "def sample():", "MCLICK timeout helper")

    abort_helper = '''_host_abort_buf = bytearray()


def _poll_host_halt():
    """Forward host HALT to the arm while the Pico waits for MCLICK."""
    global _host_abort_buf
    if serial is None:
        return False
    try:
        n = serial.in_waiting
        if n:
            _host_abort_buf.extend(serial.read(n))
    except Exception:
        return False
    saw_halt = False
    while True:
        nl = _host_abort_buf.find(b"\\n")
        if nl < 0:
            break
        raw = bytes(_host_abort_buf[:nl])
        _host_abort_buf = _host_abort_buf[nl + 1:]
        line = raw.decode("utf-8", "replace").rstrip("\\r")
        if not line:
            continue
        if line == "HALT":
            _arm_write("HALT")
            saw_halt = True
        else:
            _serial_write_line("ERR|BUSY|" + line.split("|", 1)[0])
    return saw_halt


'''
    if "def _poll_host_halt():" not in text:
        marker = "def _forward_once(line, timeout_s):" if "def _forward_once(line, timeout_s):" in text else "def forward_to_arm(line, timeout_s):"
        text = once(text, marker, abort_helper + marker, "host HALT pump")

    old_wait = '''    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        for reply in pump_arm():
            # commands are strictly serialized and mouse OKs are already filtered:
            # the first non-mouse OK/ERR we see belongs to this command.
            if reply.split("|")[0] in ("OK", "ERR"):
                return reply
        time.sleep(0.005)
    return "ERR|TIMEOUT|" + head'''
    new_wait = '''    end = time.monotonic() + timeout_s
    abort_sent = False
    while time.monotonic() < end:
        if not abort_sent and _poll_host_halt():
            abort_sent = True
        for reply in pump_arm():
            if reply.split("|")[0] in ("OK", "ERR"):
                return reply
        time.sleep(0.005)
    return ("ERR|ABORTED|" + head) if abort_sent else ("ERR|TIMEOUT|" + head)'''
    if old_wait in text:
        text = once(text, old_wait, new_wait, "abort-aware forward wait")
    elif new_wait not in text:
        raise RuntimeError("abort-aware forward wait: anchor not found")

    old_dispatch = '''    if head in MOUSE_PREFIXES:
        return forward_fast(line)
    if head in ARM_PREFIXES:'''
    new_dispatch = '''    if head == "MCLICK":
        return forward_to_arm(line, _mclick_timeout(line))
    if head in FAST_MOUSE_PREFIXES:
        return forward_fast(line)
    if head in ARM_PREFIXES:'''
    text = once(text, old_dispatch, new_dispatch, "MCLICK dispatch")

    old_plan = '''        forward_fast(line)

    def ktext(self, hmin, hmax, text):'''
    new_plan = '''        reply = forward_to_arm(line, _mclick_timeout(line))
        if reply.startswith("ERR|"):
            raise _pe.PlanAbort()

    def ktext(self, hmin, hmax, text):'''
    if old_plan in text or new_plan in text:
        text = once(text, old_plan, new_plan, "plan MCLICK dispatch")
    return text


def patch_exporter(path):
    text = path.read_text(encoding="utf-8")
    marker = 'private const string CodeTemplate = """"'
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"{path}: CodeTemplate marker missing")
    body_start = text.find("\n", start) + 1
    body_end = text.find('\n        """";', body_start)
    if body_end < 0:
        raise RuntimeError(f"{path}: CodeTemplate end missing")
    raw = text[body_start:body_end]
    body = "\n".join(line[8:] if line.startswith("        ") else line for line in raw.splitlines()) + "\n"
    patched = patch_pico_body(body)
    indented = "\n".join("        " + line if line else "        " for line in patched.rstrip("\n").splitlines()) + "\n"
    path.write_text(text[:body_start] + indented + text[body_end:], encoding="utf-8")


def patch_arm(path):
    text = path.read_text(encoding="utf-8")
    helper = '''// Keep long physical clicks HALT-abortable instead of blocking in delay(hold).
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

'''
    if "static bool wait_mouse_hold_or_abort" not in text:
        text = once(text, "// ================= command handler =================\n", helper + "// ================= command handler =================\n", "arm abort helper")
    text = once(text, "      delay(hold);\n      SingleAbsoluteMouse.release(b);", "      if (!wait_mouse_hold_or_abort((uint16_t)hold)) return;\n      SingleAbsoluteMouse.release(b);", "arm MCLICK hold")
    path.write_text(text, encoding="utf-8")


def patch_pico_file(path):
    path.write_text(patch_pico_body(path.read_text(encoding="utf-8")), encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    patch_exporter(root / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs")
    patch_pico_file(root / "firmware/pico-light-0.9.60-template.py")
    code64f = root / "firmware/code64f/code.py"
    if code64f.exists():
        patch_pico_file(code64f)
    patch_arm(root / "firmware/arm26/ams_board26.ino")
    joined = "\n".join(p.read_text(encoding="utf-8") for p in [root / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs", root / "firmware/pico-light-0.9.60-template.py", root / "firmware/arm26/ams_board26.ino"])
    for marker in ("FAST_MOUSE_PREFIXES", 'if head == "MCLICK":', "_poll_host_halt", "wait_mouse_hold_or_abort"):
        if marker not in joined:
            raise RuntimeError("missing postcondition: " + marker)


if __name__ == "__main__":
    main()
