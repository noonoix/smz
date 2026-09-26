#!/usr/bin/env python3
"""Cooperative PGROUP: HANDPATH/TYPE/WSND plus nested LOOP and RPKG."""
import random, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODERN=ROOT/'CIRCUITPY-MODERN'
sys.path.insert(0,str(MODERN))
for name in ('plan_engine','plan_engine_exec','plan_engine_human','plan_engine_parse'):
    sys.modules.pop(name,None)
import plan_engine

class Ctx:
    plan_api=3; screen_w=1920; screen_h=1080; speed_min=300; speed_max=2000; mouse_mode='relative'
    def __init__(self):
        self.t=0.0; self.ev=[]; self.sound=False
    def now(self): return self.t
    def gate(self): return True
    def sleep_ms(self,ms): self.t+=ms/1000.0; self.ev.append(('sleep',ms)); return True
    def log(self,s): self.ev.append(('log',s))
    def mmove_relative(self,dx,dy): self.ev.append(('move',round(self.t,3),dx,dy))
    def mmove(self,x,y): self.ev.append(('abs',round(self.t,3),x,y))
    def type_char(self,ch): self.ev.append(('char',round(self.t,3),ch))
    def ktext(self,a,z,s): self.ev.append(('text',round(self.t,3),s))
    def kcombo(self,v): self.ev.append(('combo',round(self.t,3),v))
    def key_combo(self,v,a,z): self.ev.append(('key',round(self.t,3),tuple(v)))
    def sound_start(self,thr,minimum,timeout): self.sound=True; self.ev.append(('sound-start',round(self.t,3)))
    def sound_poll(self):
        self.ev.append(('sound-poll',round(self.t,3)))
        return True if self.t>=0.055 else None
    def sound_cancel(self): self.sound=False; self.ev.append(('sound-cancel',round(self.t,3)))

plan='''PLAN|2
PGROUP
LOOP|2
RPKG|seq,0,1
HANDPATH|20,2,0;20,0,2
ENDPKG
ENDLOOP
PARITEM
LOOP|1
WSND|90,60,500
TYPE|h=15,15|text=ok
KEY|combo=13
ENDLOOP
ENDPAR'''
ctx=Ctx(); random.seed(4)
ops=plan_engine.parse_plan(plan)
plan_engine.run_plan(ops,ctx)
moves=[e for e in ctx.ev if e[0]=='move']
chars=[e for e in ctx.ev if e[0]=='char']
assert len(moves)==4,moves
assert ''.join(e[2] for e in chars)=='ok',chars
# Mouse reports continue while the sound branch is listening.
assert any(e[0]=='move' and 0.0 < e[1] < 0.055 for e in ctx.ev),ctx.ev
assert chars[0][1] < moves[-1][1],ctx.ev
assert any(e[0]=='sound-start' for e in ctx.ev),ctx.ev
assert ('key',ctx.ev[-1][1],(13,)) in ctx.ev or any(e[0]=='key' and e[2]==(13,) for e in ctx.ev),ctx.ev
# Parser must still fail closed for the Arm-owned blocking sound/click transaction.
bad='PLAN|2\nPGROUP\nTRGSND|90,60,500,1,80,180,30,90\nPARITEM\nDELAY|1\nENDPAR'
try:
    plan_engine.parse_plan(bad)
except ValueError as exc:
    assert 'not allowed inside PGROUP' in str(exc),exc
else:
    raise AssertionError('TRGSND unexpectedly accepted')
print('cooperative parallel runtime: 8 passed, 0 failed')
