#!/usr/bin/env python3
import importlib.util
from pathlib import Path
root=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('rw',root/'portable/plan3/CIRCUITPY/restart_windows.py');rw=importlib.util.module_from_spec(spec);spec.loader.exec_module(rw)
class Rng:
 def __init__(self):self.draws=[]
 def randint(self,lo,hi):self.draws.append((lo,hi));return lo+(hi-lo)//2
class Ctx:
 def __init__(self):self.events=[]
 def kdown(self,vk):self.events.append(('down',vk))
 def kup(self,vk):self.events.append(('up',vk))
 def sleep_ms(self,ms):self.events.append(('sleep',ms));return True
ctx=Ctx();rng=Rng();rw.perform(ctx,rng)
keys=[x for x in ctx.events if x[0]!='sleep']
assert keys[:14]==[('down',91),('down',88),('up',88),('up',91),('down',38),('up',38),('down',38),('up',38),('down',13),('up',13),('down',38),('up',38),('down',13),('up',13)]
# Shutdown blocker: Shift remains down throughout the complete Tab press/release.
assert keys[14:18]==[('down',16),('down',9),('up',9),('up',16)]
assert keys[18:]==[('down',13),('up',13)]
assert (5200,6000) in rng.draws and (320,480) in rng.draws and (160,240) in rng.draws and (180,300) in rng.draws
print('restart windows accepted sequence: 20 passed, 0 failed')
