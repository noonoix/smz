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
assert 'plan_engine_parallel' not in sys.modules, 'parallel scheduler imported before PGROUP'

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
assert 'plan_engine_parallel' in sys.modules, 'parallel scheduler was not loaded at PGROUP'
moves=[e for e in ctx.ev if e[0]=='move']
chars=[e for e in ctx.ev if e[0]=='char']
assert 1 <= len(moves) < 4,moves
assert ''.join(e[2] for e in chars)=='ok',chars
# Mouse reports continue while listening, then sound success cancels siblings.
assert any(e[0]=='move' and 0.0 < e[1] < 0.055 for e in ctx.ev),ctx.ev
assert all(e[1] <= chars[0][1] for e in moves),ctx.ev
assert ('log','parallel wsnd heard - cancel siblings') in ctx.ev,ctx.ev
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

# A large portable RMOUSE inside PGROUP must use the bounded streaming curve,
# not allocate the dense 2–3 px plan that exhausted the Pico after ~100 seconds.
import plan_engine_parallel as parallel
original_plan_move=parallel.plan_move
def forbidden_dense_plan(*args,**kwargs):
    raise AssertionError('relative PGROUP RMOUSE called dense plan_move')
parallel.plan_move=forbidden_dense_plan
try:
    random.seed(11)
    pos=[960,540]
    events=list(parallel._parallel_mouse_events({
        'region':(1301,0,378,1049),'before':(20,85),'after':(20,103),
        'curve':(0,3),'mid':(36,(144,375)),'over':2,'mt':(16,159),
        'idle':((5,12),(800,3000))
    },Ctx(),plan_engine.PausePlanner(),pos))
finally:
    parallel.plan_move=original_plan_move
stream_moves=[e for e in events if e[0]=='move']
assert 6 <= len(stream_moves) <= 24,len(stream_moves)
assert sum(e[2] for e in stream_moves)==pos[0]-960
assert sum(e[3] for e in stream_moves)==pos[1]-540
assert all(e[4] is True for e in stream_moves)

# A sampled speed band is authoritative when mt is absent. Account for ARM's
# own micro-step time so the Pico does not pay the recorded cadence twice.
random.seed(12)
speed_events=list(parallel._parallel_relative_mouse_events(
    {},Ctx(),plan_engine.PausePlanner(),[960,540],
    dict(parallel._DEFAULT_CFG, speed_min=500, speed_max=500, mt_min=0, mt_max=0,
         before_min=0,before_max=0,after_min=0,after_max=0,
         mid_chance=0,idle_pause_max=0),1260,540))
speed_moves=[e for e in speed_events if e[0]=='move']
assert 8 <= len(speed_moves) <= 32,len(speed_moves)
# 300 px at 500 px/s targets 600 ms; ARM supplies ~300 ms, so waits total 300.
assert sum(e[1] for e in speed_moves)==300,speed_moves
print('cooperative parallel runtime: 12 passed, 0 failed')
