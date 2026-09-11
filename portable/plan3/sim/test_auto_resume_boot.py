#!/usr/bin/env python3
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("arb", root / "portable/plan3/CIRCUITPY/auto_resume_boot.py")
arb = importlib.util.module_from_spec(spec); spec.loader.exec_module(arb)

class Store:
    def __init__(self, armed=True): self.armed = armed; self.clears = 0
    def is_armed(self): return self.armed
    def arm(self): self.armed = True
    def clear(self): self.armed = False; self.clears += 1
class Rng:
    def __init__(self, value=4): self.value=value; self.calls=[]
    def randint(self, lo, hi): self.calls.append((lo,hi)); return self.value

# Armed at Pico boot proves a power-cycle; UP may settle immediately.
now=[0.0]; state=["UP"]; starts=[]; store=Store(True); rng=Rng(4)
b=arb.AutoResumeBoot(store,lambda:now[0],lambda:state[0]=="UP",lambda:starts.append(now[0]) or True,
                     rng=rng,usb_down=lambda:state[0] in ("DOWN","SUSPEND"),stable_seconds=12)
b.configure(True,3,5)
assert b.disconnect_seen and b.tick()==arb.BOOT_SETTLE and b.start_at==16
now[0]=15.9; assert b.tick()==arb.BOOT_SETTLE
now[0]=16; assert b.tick()==arb.IDLE and starts==[16] and store.clears==1

# Late arm while Pico stays powered MUST see DOWN/SUSPEND before accepting UP.
store=Store(False); now[0]=0; state[0]="UP"; starts=[]
b=arb.AutoResumeBoot(store,lambda:now[0],lambda:state[0]=="UP",lambda:starts.append(1) or True,
                     usb_down=lambda:state[0] in ("DOWN","SUSPEND"),stable_seconds=2)
b.configure(True,1,1); store.arm()
assert b.tick()==arb.WAIT_FOR_HOST and not b.disconnect_seen
state[0]="SUSPEND"; assert b.tick()==arb.WAIT_FOR_HOST and b.disconnect_seen
state[0]="UP"; assert b.tick()==arb.BOOT_SETTLE and b.start_at==3
now[0]=3; assert b.tick()==arb.IDLE and starts==[1]

# A reconnect drop during settle restarts the complete stable window and redraws.
store=Store(False); store.arm(); now[0]=0; state[0]="DOWN"; rng=Rng(2)
b=arb.AutoResumeBoot(store,lambda:now[0],lambda:state[0]=="UP",lambda:True,rng=rng,
                     usb_down=lambda:state[0]!="UP",stable_seconds=5); b.configure(True,1,3)
b.tick(); state[0]="UP"; b.tick(); assert b.start_at==7
now[0]=4; state[0]="DOWN"; assert b.tick()==arb.WAIT_FOR_HOST
now[0]=6; state[0]="UP"; b.tick(); assert b.start_at==13 and rng.calls==[(1,3),(1,3)]

# Ordinary boot without marker never starts; cancel and failed start stay fail-safe.
store=Store(False); state[0]="UP"; b=arb.AutoResumeBoot(store,lambda:0,lambda:True,lambda:True,usb_down=lambda:False)
assert b.tick()==arb.IDLE
store=Store(True); b=arb.AutoResumeBoot(store,lambda:0,lambda:True,lambda:False,usb_down=lambda:False,stable_seconds=0)
b.configure(True,0,0); b.tick(); assert b.tick()==arb.WAIT_FOR_HOST and store.armed
store=Store(True); b=arb.AutoResumeBoot(store,lambda:0,lambda:True,lambda:True,lambda:True,usb_down=lambda:False)
assert b.tick()==arb.IDLE and store.clears==1
print("auto resume host lifecycle: 29 passed, 0 failed")
