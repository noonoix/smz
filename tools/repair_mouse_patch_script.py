from pathlib import Path

p = Path("tools/apply_mouse_reliability.py")
s = p.read_text(encoding="utf-8")
replacements = {
    "indent + '''if line.startswith(\"EVT|\"):\\n''' + indent + '''    _serial_write_line(line)              # arm events reach the PC live\\n''' + indent + '''    continue'''":
    "indent + '''        if line.startswith(\"EVT|\"):\\n''' + indent + '''            _serial_write_line(line)              # arm events reach the PC live\\n''' + indent + '''            continue'''",
    "indent + '''if line.startswith(\"EVT|\"):\\n''' + indent + '''    if line.startswith(\"EVT|HOSTUSB|\"):\\n''' + indent + '''        if line == _last_hostusb_event[0]:\\n''' + indent + '''            continue\\n''' + indent + '''        _last_hostusb_event[0] = line\\n''' + indent + '''    _serial_write_line(line)              # changed events reach the PC once\\n''' + indent + '''    continue'''":
    "indent + '''        if line.startswith(\"EVT|\"):\\n''' + indent + '''            if line.startswith(\"EVT|HOSTUSB|\"):\\n''' + indent + '''                if line == _last_hostusb_event[0]:\\n''' + indent + '''                    continue\\n''' + indent + '''                _last_hostusb_event[0] = line\\n''' + indent + '''            _serial_write_line(line)              # changed events reach the PC once\\n''' + indent + '''            continue'''",
    "indent + '''if head in MOUSE_PREFIXES:\\n''' + indent + '''    return forward_fast(line)\\n''' + indent + '''if head in ARM_PREFIXES:'''":
    "indent + '''    if head in MOUSE_PREFIXES:\\n''' + indent + '''        return forward_fast(line)\\n''' + indent + '''    if head in ARM_PREFIXES:'''",
    "indent + '''if head == \"MCLICK\":\\n''' + indent + '''    return forward_to_arm(line, _mclick_timeout(line))\\n''' + indent + '''if head in FAST_MOUSE_PREFIXES:\\n''' + indent + '''    return forward_fast(line)\\n''' + indent + '''if head in ARM_PREFIXES:'''":
    "indent + '''    if head == \"MCLICK\":\\n''' + indent + '''        return forward_to_arm(line, _mclick_timeout(line))\\n''' + indent + '''    if head in FAST_MOUSE_PREFIXES:\\n''' + indent + '''        return forward_fast(line)\\n''' + indent + '''    if head in ARM_PREFIXES:'''",
}
for old, new in replacements.items():
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"repair expected one match, found {count}: {old[:90]!r}")
    s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
print("patch-script indentation repaired")
