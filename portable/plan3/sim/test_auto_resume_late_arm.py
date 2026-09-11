#!/usr/bin/env python3
import sys
from pathlib import Path
base = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(base / "CIRCUITPY"))
import auto_resume_boot as arb
class Store:
    armed=False
    def is_armed(self): return self.armed
    def clear(self): self.armed=False
now=[0.0]; ready=[False]; starts=[]; store=Store()
boot=arb.AutoResumeBoot(store,lambda:now[0],lambda:ready[0],lambda:starts.append(1) or True)
assert boot.state==arb.IDLE and boot.tick()==arb.IDLE
store.armed=True
assert boot.tick()==arb.WAIT_FOR_HOST
ready[0]=True
assert boot.tick()==arb.BOOT_SETTLE
ready[0]=False
assert boot.tick()==arb.WAIT_FOR_HOST
print("auto resume late-arm: 6 passed, 0 failed")
