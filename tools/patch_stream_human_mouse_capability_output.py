#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text(encoding='utf-8')
old='''def _mouse_profile(owner, values):
    speed=getattr(owner,"route_speed",(150,500))'''
new='''def _mouse_profile(owner, values):
    cap=owner.arm.send("HVER",3)
    if not cap.startswith("OK|HVER|2.7.0|HMOUSE=1"):
        raise RuntimeError("ARM 2.7 human mouse capability required")
    speed=getattr(owner,"route_speed",(150,500))'''
if old in s:s=s.replace(old,new,1)
elif new not in s:
    if 'ARM 2.7 human mouse capability required' not in s:
        raise SystemExit('missing HVER capability anchor')
p.write_text(s,encoding='utf-8',newline='\n');print('patched ARM 2.7 capability gate:',p)
