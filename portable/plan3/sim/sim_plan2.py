#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardware-free behavioural tests for plan_engine v2."""
import sys, random
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _cand in (_HERE, _ROOT, os.path.join(_ROOT, "CIRCUITPY"), os.path.join(_ROOT, "tools"),
              os.path.join(_HERE, "CIRCUITPY"), os.path.join(_HERE, "tools"), os.getcwd()):
    if os.path.exists(os.path.join(_cand, "plan_engine.py")):
        sys.path.insert(0, _cand)
import plan_engine as pe

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print("PASS", name)
    else: FAIL += 1; print("FAIL", name)

class Ctx:
    plan_api = 2
    screen_w = 1920; screen_h = 1080; speed_min = 0; speed_max = 2000
    def __init__(self, snd=(), lux=(), files=None):
        self.t=0.0; self.snd=list(snd); self.lux=list(lux); self.files=files or {}; self.ev=[]; self.pos=None
    def now(self): return self.t
    def sleep_ms(self, ms): self.t += ms/1000; self.ev.append(("delay",ms)); return True
    def get_mouse_pos(self): return self.pos
    def set_mouse_pos(self,x,y): self.pos=(int(x),int(y))
    def mmove(self,x,y): self.ev.append(("move",int(x),int(y)))
    def mclick(self,b,n,a,z): self.ev.append(("click",b,n,a,z))
    def ktext(self,a,z,s): self.ev.append(("text",a,z,s))
    def kcombo(self,v): self.ev.append(("combo1",v))
    def wait_light(self,*a): self.ev.append(("lux",)+a); return self.lux.pop(0) if self.lux else False
    def key(self,v,h): self.ev.append(("key",v,h))
    def log(self,s): self.ev.append(("log",s))
    def wait_sound(self,*a): self.ev.append(("sound",)+a); return self.snd.pop(0) if self.snd else False
    def trg_sound(self,*a): self.ev.append(("trgsnd",)+a); return True
    def key_combo(self,v,a,z): self.ev.append(("keycombo",tuple(v),a,z))
    def kdown(self,v): self.ev.append(("down",v))
    def kup(self,v): self.ev.append(("up",v))
    def wheel(self,v): self.ev.append(("wheel",v))
    def raw(self,s): self.ev.append(("raw",s)); return "OK|RAW"
    def read_plan_file(self,n): return self.files[n]
    def setres(self,w,h): self.ev.append(("setres",w,h))

def run(text, **kw):
    c=Ctx(**kw); random.seed(7); pe.run_plan(pe.parse_plan(text),c); return c

def expect_error(name,text,contains):
    try: pe.parse_plan(text)
    except Exception as e: check(name, contains in str(e))
    else: check(name,False)

# parser/linker
p=pe.parse_plan("PLAN|2\nIFSND|60,100,1000\nKEY|combo=17+65\nELSE\nWHEEL|-2\nENDIF")
check("PLAN|2 accepted",p[0][1]["v"]==2)
check("IF links then/else/endif",p[1][1]["else_ip"]==4 and p[1][1]["endif_ip"]==6 and p[3][1]["endif_ip"]==6)
expect_error("duplicate ELSE rejected","PLAN|2\nIFSND|1,1,1\nELSE\nELSE\nENDIF","duplicate ELSE")
expect_error("orphan ENDIF rejected","PLAN|2\nENDIF","without IFSND")
expect_error("missing label rejected","PLAN|2\nGOTO|nope","no matching LABEL")
expect_error("include traversal rejected","PLAN|2\nINCLUDE|file=../x.txt","plain *.txt")

# then and else
text="PLAN|2\nSCREEN|1920,1080\nIFSND|60,100,1000\nKEY|combo=17+65|hold=30,40\nELSE\nWHEEL|-2\nENDIF\nKDOWN|16\nKUP|16\nRAW|MCLICK|left"
c=run(text,snd=[True])
check("SCREEN calls SETRES once",sum(e[0]=="setres" for e in c.ev)==1)
check("IFSND true executes Then",any(e[0]=="keycombo" for e in c.ev) and not any(e[0]=="wheel" for e in c.ev))
check("key combo preserves VKs",("keycombo",(17,65),30,40) in c.ev)
check("KDOWN/KUP/RAW execute",("down",16) in c.ev and ("up",16) in c.ev and ("raw","MCLICK|left") in c.ev)
c=run(text,snd=[False])
check("IFSND false executes Else",("wheel",-2) in c.ev and not any(e[0]=="keycombo" for e in c.ev))

# IFLUX and WSND timeout-continues
text="PLAN|2\nWSND|50,80,500\nIFLUX|10,20,100,500,1\nKDOWN|65\nELSE\nKUP|65\nENDIF"
c=run(text,snd=[False],lux=[True])
check("plain WSND timeout continues",any(e[0]=="lux" for e in c.ev))
check("IFLUX true Then",("down",65) in c.ev and ("up",65) not in c.ev)
c=run(text,snd=[True],lux=[False])
check("IFLUX false Else",("up",65) in c.ev and ("down",65) not in c.ev)

# armed sound positional contract
c=run("PLAN|2\nTRGSND|60,100,30000,1,80,180,30,90")
check("TRGSND eight-number contract",("trgsnd",60,100,30000,1,80,180,30,90) in c.ev)

# loops/time: each pass may cross deadline, then stops after ENDLOOP
c=run("PLAN|2\nLOOP|3\nDELAY|100\nENDLOOP")
check("LOOP count exact",sum(e[0]=="delay" for e in c.ev)==3)
c=run("PLAN|2\nLOOPTIME|0.25\nDELAY|100\nENDLOOP")
check("LOOPTIME completes crossing pass",sum(e[0]=="delay" for e in c.ev)==3 and abs(c.t-.3)<1e-9)

# include + cycle/depth are non-fatal
files={"child.txt":"PLAN|2\nKDOWN|70\nINCLUDE|file=child.txt"}
c=run("PLAN|2\nINCLUDE|file=child.txt\nKUP|70",files=files)
check("INCLUDE executes child",("down",70) in c.ev and ("up",70) in c.ev)
check("INCLUDE cycle is logged and skipped",any(e[0]=="log" and "cycle" in e[1] for e in c.ev))

# MOVETO instant path should produce exact target and persist it
c=run("PLAN|2\nSCREEN|1920,1080\nMOVETO|x=321|y=654|human=0")
check("MOVETO instant lands exactly",("move",321,654) in c.ev and c.pos==(321,654))

# plan_api gate
class Old(Ctx): plan_api=1
try: pe.run_plan(pe.parse_plan("PLAN|2\nWHEEL|1"),Old())
except ValueError as e: check("v2 ops reject old ctx","plan_api 1" in str(e))
else: check("v2 ops reject old ctx",False)

print("=== Results: %d passed, %d failed ==="%(PASS,FAIL))
sys.exit(1 if FAIL else 0)
