#!/usr/bin/env python3
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

helper = '''def _arm_send_cooperative(owner, line, timeout=5):
    # Mouse/HID calls must continue servicing GP4/GP3, host commands and UART
    # while the Pro Micro is acknowledging a human-mouse command.
    owner.arm.pump()
    owner.arm.write(line)
    head = line.split("|", 1)[0]
    end = runtime.time.monotonic() + timeout
    while runtime.time.monotonic() < end:
        owner.host_poll()
        owner.buttons()
        for reply in owner.arm.pump():
            if reply.startswith("OK|" + head) or reply.startswith("ERR|"):
                return reply
        if not owner.controls.running and not owner.calibrating:
            return "ERR|STOPPED"
        runtime.time.sleep(.002)
    raise RuntimeError("arm acknowledgement timeout: " + head)


'''
anchor = 'def _mouse_profile(owner, values):\n'
if helper not in s:
    if anchor not in s: raise SystemExit("missing mouse profile anchor")
    s = s.replace(anchor, helper + anchor, 1)

repls = {
    'cap=owner.arm.send("HVER",3)': 'cap=_arm_send_cooperative(owner,"HVER",3)',
    'if not owner.arm.send(cfg,3).startswith("OK|")': 'if not _arm_send_cooperative(owner,cfg,3).startswith("OK|")',
    'if not owner.arm.send(pauses,3).startswith("OK|")': 'if not _arm_send_cooperative(owner,pauses,3).startswith("OK|")',
    'reply=owner.arm.send("MMOVE|%d,%d,abs,0"%(x,y),8)': 'reply=_arm_send_cooperative(owner,"MMOVE|%d,%d,abs,0"%(x,y),8)',
    'reply=owner.arm.send("HMOVE|%d,%d"%(x,y),35)': 'reply=_arm_send_cooperative(owner,"HMOVE|%d,%d"%(x,y),35)',
    'reply=owner.arm.send("HRANDOM|%d,%d,%d,%d"%(x,y,w,h),35)': 'reply=_arm_send_cooperative(owner,"HRANDOM|%d,%d,%d,%d"%(x,y,w,h),35)',
}
for old, new in repls.items():
    if old in s: s = s.replace(old, new, 1)
    elif new not in s: raise SystemExit("missing mouse call anchor: " + old)

if '_arm_send_cooperative(owner' not in s:
    raise SystemExit("cooperative mouse postcondition failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched cooperative human mouse:", p)
