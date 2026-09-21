#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
helper=r'''def _mouse_pair(value, default):
    if value is None: return default
    a=value.split(",")
    if len(a)!=2: raise ValueError("bad mouse range")
    lo=int(a[0]); hi=int(a[1])
    if lo<0 or hi<0 or hi<lo: raise ValueError("invalid mouse range")
    return lo,hi


def _mouse_profile(owner, values):
    speed=getattr(owner,"route_speed",(150,500))
    mt=_mouse_pair(values.get("mt"),(0,0))
    curve=_mouse_pair(values.get("curve"),(15,45))
    before=_mouse_pair(values.get("before"),(120,450))
    after=_mouse_pair(values.get("after"),(150,600))
    mid=(12,100,400)
    if "mid" in values:
        a=values["mid"].split(":",1)
        if len(a)!=2: raise ValueError("bad mouse mid")
        r=_mouse_pair(a[1],(100,400)); mid=(int(a[0]),r[0],r[1])
    idle=(5,12,800,3000)
    if "idle" in values:
        a=values["idle"].split(":",1)
        if len(a)!=2: raise ValueError("bad mouse idle")
        every=_mouse_pair(a[0],(5,12)); pause=_mouse_pair(a[1],(800,3000))
        idle=(every[0],every[1],pause[0],pause[1])
    over=int(values.get("over","15"))
    if not 0<=mid[0]<=100 or not 0<=over<=100: raise ValueError("mouse chance out of range")
    cfg="HCFG|%d,%d,%d,%d,%d,%d,%d,%d,%d,%d"%(speed[0],speed[1],mt[0],mt[1],curve[0],curve[1],before[0],before[1],after[0],after[1])
    pauses="HPAUSE|%d,%d,%d,%d,%d,%d,%d,%d"%(mid[0],mid[1],mid[2],idle[0],idle[1],idle[2],idle[3],over)
    if not owner.arm.send(cfg,3).startswith("OK|"): raise RuntimeError("ARM HCFG rejected")
    if not owner.arm.send(pauses,3).startswith("OK|"): raise RuntimeError("ARM HPAUSE rejected")


def _mouse_values(args):
    values={}
    for field in args.split("|"):
        if "=" not in field: raise ValueError("bad mouse field")
        k,v=field.split("=",1)
        if k in values: raise ValueError("duplicate mouse field")
        values[k]=v
    return values


def _light_mouse(owner,op,args,expected):
    values=_mouse_values(args)
    if not _light_gate(owner,expected): return False
    if op=="MOVETO":
        if "x" not in values or "y" not in values: raise ValueError("MOVETO needs x/y")
        x=int(values["x"]); y=int(values["y"]); human=int(values.get("human","1"))
        if human==0:
            reply=owner.arm.send("MMOVE|%d,%d,abs,0"%(x,y),8)
        else:
            _mouse_profile(owner,values); reply=owner.arm.send("HMOVE|%d,%d"%(x,y),35)
    else:
        if "region" not in values: raise ValueError("RMOUSE needs region")
        a=values["region"].split(",")
        if len(a)!=4: raise ValueError("bad RMOUSE region")
        x,y,w,h=(int(v) for v in a)
        if w<1 or h<1: raise ValueError("bad RMOUSE region")
        _mouse_profile(owner,values); reply=owner.arm.send("HRANDOM|%d,%d,%d,%d"%(x,y,w,h),35)
    if not reply.startswith("OK|"): raise RuntimeError("ARM human mouse rejected")
    owner.emit("EVT|DEBUG|STEP/%s arm27=ok"%op)
    return _light_gate(owner,expected)

'''
anchor='def _run_light_route(owner, name):\n'
if helper not in s:
    if anchor not in s: raise SystemExit('missing human mouse helper anchor')
    s=s.replace(anchor,helper+anchor,1)
s=s.replace('"KDOWN", "KUP", "TYPE"}', '"KDOWN", "KUP", "TYPE", "RMOUSE", "MOVETO"}',1)
old='''            elif op == "SCREEN":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SCREEN")
            elif op == "SPEED":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SPEED")'''
new='''            elif op == "SCREEN":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SCREEN")
                w=int(a[0]); h=int(a[1])
                if w<1 or h<1: raise ValueError("bad SCREEN")
                owner.route_screen=(w,h)
                if not owner.arm.send("SETRES|%d,%d"%(w,h),3).startswith("OK|"): raise RuntimeError("ARM SETRES rejected")
            elif op == "SPEED":
                a = args.split(",")
                if len(a) != 2: raise ValueError("bad SPEED")
                lo=int(a[0]); hi=int(a[1])
                if lo<0 or hi<lo: raise ValueError("bad SPEED")
                owner.route_speed=(lo,hi)'''
if old in s:s=s.replace(old,new,1)
elif new not in s:raise SystemExit('missing mouse metadata anchor')
old2='''            elif op == "TYPE":
                if not _light_type(owner, args, expected): return
            elif op in ("KDOWN", "KUP"):'''
new2='''            elif op == "TYPE":
                if not _light_type(owner, args, expected): return
            elif op in ("RMOUSE", "MOVETO"):
                if not _light_mouse(owner, op, args, expected): return
            elif op in ("KDOWN", "KUP"):'''
if old2 in s:s=s.replace(old2,new2,1)
elif new2 not in s:raise SystemExit('missing mouse dispatch anchor')
p.write_text(s,encoding='utf-8',newline='\n');print('patched streaming human mouse:',p)
