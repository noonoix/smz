"""Root cycle state with persistent bounded restart accounting."""
import os, random, time
ARMED_TEXT="AUTO_RESUME_ARMED"; _ARMED_BYTES=ARMED_TEXT.encode("ascii"); _COUNT_INDEX=len(_ARMED_BYTES)+1; DEFAULT_MAX_RESTARTS=5
try: import microcontroller; _NVM=microcontroller.nvm
except Exception: _NVM=None
class PlanDeadline(Exception): pass
class ResumeArmStore:
 def __init__(self,path=".auto_resume_armed"): self.path=path; self.count_path=path+".restarts"
 def _nvm_available(self): return _NVM is not None and len(_NVM)>_COUNT_INDEX
 def arm(self):
  if self._nvm_available(): _NVM[0:len(_ARMED_BYTES)]=_ARMED_BYTES; _NVM[len(_ARMED_BYTES)]=0xA5; return
  with open(self.path,"w") as f: f.write(ARMED_TEXT)
 def is_armed(self):
  if self._nvm_available():
   try: return bytes(_NVM[0:len(_ARMED_BYTES)])==_ARMED_BYTES and _NVM[len(_ARMED_BYTES)]==0xA5
   except Exception: return False
  try:
   with open(self.path) as f: return f.read().strip()==ARMED_TEXT
  except OSError: return False
 def restart_count(self):
  if self._nvm_available():
   try: return int(_NVM[_COUNT_INDEX])
   except Exception: return 0
  try:
   with open(self.count_path) as f: return max(0,int(f.read().strip()))
  except Exception: return 0
 def _write_count(self,n):
  n=max(0,min(255,int(n)))
  if self._nvm_available(): _NVM[_COUNT_INDEX]=n; return
  with open(self.count_path,"w") as f: f.write(str(n))
 def try_arm_restart(self,maximum=DEFAULT_MAX_RESTARTS,auto_resume=True):
  n=self.restart_count()
  if n>=max(0,int(maximum)): self.clear(); return False
  self._write_count(n+1)
  if auto_resume: self.arm()
  else: self.clear()
  return True
 def reset_restart_count(self):
  if self._nvm_available(): _NVM[_COUNT_INDEX]=0; return
  try: os.remove(self.count_path)
  except OSError: pass
 def consume(self):
  armed=self.is_armed()
  if armed: self.clear()
  return armed
 def clear(self):
  if self._nvm_available():
   try:
    for i in range(len(_ARMED_BYTES)+1): _NVM[i]=0
   except Exception: pass
   return
  try: os.remove(self.path)
  except OSError: pass
class RootCycle:
 def __init__(self,now=None,rng=None,arm_store=None,max_restarts=DEFAULT_MAX_RESTARTS):
  self.now=now or time.monotonic; self.rng=rng or random; self.arm_store=arm_store or ResumeArmStore(); self.max_restarts=max(0,int(max_restarts)); self.started_at=None; self.deadline=None; self.runtime_seconds=None; self.auto_resume_enabled=False; self.resume_range=(180,300); self.resume_delay_seconds=None; self.stopped=False; self.failed=False; self.expired_naturally=False; self.restart_started=False; self.restart_limit_reached=False
 @staticmethod
 def _positive_range(lo,hi,name):
  lo,hi=int(lo),int(hi)
  if hi<lo: lo,hi=hi,lo
  if lo<=0: raise ValueError(name+" range must be positive")
  return lo,hi
 def configure(self,a,b,enabled,c,d):
  if self.started_at is not None: raise RuntimeError("cycle already started")
  self.run_range=self._positive_range(a,b,"RUNFOR"); self.resume_range=self._positive_range(c,d,"AUTORESUME"); self.auto_resume_enabled=bool(enabled)
 def start(self):
  if self.started_at is not None: return self.runtime_seconds
  if not hasattr(self,"run_range"): raise RuntimeError("RUNFOR is not configured")
  self.started_at=float(self.now()); self.runtime_seconds=self.rng.randint(*self.run_range); self.deadline=self.started_at+self.runtime_seconds; return self.runtime_seconds
 def gate(self):
  if self.stopped: raise RuntimeError("cycle stopped")
  if self.failed: raise RuntimeError("cycle failed")
  if self.deadline is not None and float(self.now())>=self.deadline: self.expired_naturally=True; raise PlanDeadline()
 def stop(self): self.stopped=True; self.arm_store.clear()
 def fail(self): self.failed=True; self.arm_store.clear()
 def reset_restart_session(self): self.arm_store.clear(); self.arm_store.reset_restart_count()
 def arm_natural_restart(self,release_all):
  if not self.expired_naturally or self.stopped or self.failed or self.restart_started: return False
  release_all()
  if not self.arm_store.try_arm_restart(self.max_restarts,self.auto_resume_enabled): self.restart_limit_reached=True; self.stopped=True; return False
  self.restart_started=True; return True
 def consume_resume_on_boot(self):
  if not self.arm_store.consume() or not self.auto_resume_enabled: return None
  if self.resume_delay_seconds is None: self.resume_delay_seconds=self.rng.randint(*self.resume_range)
  return self.resume_delay_seconds
