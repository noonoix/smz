from pathlib import Path

p = Path("tools/sync_autocycle_mouse.py")
s = p.read_text(encoding="utf-8")
old = '''        code=code.Replace("_last_hostusb_event = [None]  # forward identical HOSTUSB heartbeats once\\n","",StringComparison.Ordinal);\n'''
new = '''        code=RequireReplace(code,"parts[1] in FAST_MOUSE_PREFIXES","parts[1] in MOUSE_PREFIXES","normal mouse ACK filter");\n''' + old
if s.count(old) != 1:
    raise SystemExit(f"expected one ACK normalization anchor, found {s.count(old)}")
p.write_text(s.replace(old, new), encoding="utf-8")
print("AutoCycle ACK filter baseline normalized")
