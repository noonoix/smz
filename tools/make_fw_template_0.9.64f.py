#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
TARGET_VERSION="0.9.64f"
VALUES={"__MACHINE__":"sim","__GENERATED__":"2026-09-09","__VERSION__":TARGET_VERSION,"__STATE_COUNT__":"0","__LOOP_MODE__":"once","__LOOP_COUNT__":"0","__LOOP_SECONDS__":"0"}
EXPECTED={"__MACHINE__":1,"__GENERATED__":1,"__VERSION__":3,"__STATE_COUNT__":1,"__LOOP_MODE__":1,"__LOOP_COUNT__":1,"__LOOP_SECONDS__":1}
def once(t,o,n,l):
 c=t.count(o)
 if c!=1: raise SystemExit(f"ERROR: {l}: expected one anchor, found {c}")
 return t.replace(o,n,1)
def body(g):
 g=once(g,"# Classroom Studio v0.9.64f - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)","# Classroom Studio v__VERSION__ - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)","title")
 g=once(g,"# System: sim   generated: 2026-09-09   calibrated states: 0","# System: __MACHINE__   generated: __GENERATED__   calibrated states: __STATE_COUNT__","metadata")
 g=once(g,'LOOP_MODE = "once"','LOOP_MODE = "__LOOP_MODE__"',"mode")
 g=once(g,"LOOP_COUNT = 0 ","LOOP_COUNT = __LOOP_COUNT__ ","count")
 g=once(g,"LOOP_SECONDS = 0","LOOP_SECONDS = __LOOP_SECONDS__","seconds")
 g=once(g,"pico-light 0.9.64f|role=brain+keyboard+light","pico-light __VERSION__|role=brain+keyboard+light","pong")
 g=once(g,"pico-light 0.9.64f | GP4=NumLock","pico-light __VERSION__ | GP4=NumLock","banner")
 if '""""' in g: raise SystemExit("ERROR: four quotes")
 return g
def extract(cs):
 m='    private const string CodeTemplate = """"\n'; s=cs.index(m)+len(m); e=cs.index('\n        """";',s); out=[]
 for line in cs[s:e].split('\n'):
  if not line: out.append("")
  elif line.startswith("        "): out.append(line[8:])
  else: raise SystemExit("ERROR: raw indent")
 return '\n'.join(out)
def verify(cs,g):
 t=extract(cs); counts={k:t.count(k) for k in VALUES}
 if counts!=EXPECTED: raise SystemExit(f"ERROR: placeholders {counts}")
 x=t
 for k,v in VALUES.items(): x=x.replace(k,v)
 if x!=g: raise SystemExit("ERROR: export differs from golden")
 print("PASS byte-identical "+hashlib.sha256(x.encode()).hexdigest())
def main():
 root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
 cp=root/'ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs'; pp=root/'ams-shell/src/Ams.UI/Services/PlanExporter.cs'; g=(root/'firmware/code64f/code.py').read_text(encoding='utf-8'); cs=cp.read_text(encoding='utf-8'); b=body(g); ind='\n'.join(('        '+x) if x else '' for x in b.split('\n')); s=cs.index('    private const string CodeTemplate = """"'); e=cs.index('\n        """";',s)+len('\n        """";'); cs=cs[:s].replace('0.9.64b','0.9.64f')+'    private const string CodeTemplate = """"\n'+ind+'\n        """";'+cs[e:].replace('0.9.64b','0.9.64f'); cp.write_text(cs,encoding='utf-8',newline=''); p=pp.read_text(encoding='utf-8'); p=once(p,'public const string EngineVersion = "0.9.64b";','public const string EngineVersion = "0.9.64f";',"engine"); pp.write_text(p,encoding='utf-8',newline=''); verify(cs,g)
if __name__=='__main__': main()
