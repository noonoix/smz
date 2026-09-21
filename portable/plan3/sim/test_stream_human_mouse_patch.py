#!/usr/bin/env python3
from pathlib import Path
import py_compile,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'code.py';shutil.copyfile(root/'firmware/pico-light-guard-1.0.0/code.py',p)
 subprocess.run([sys.executable,str(root/'tools/patch_combined_runtime_output.py'),str(p)],check=True)
 subprocess.run([sys.executable,str(root/'tools/patch_stream_type_output.py'),str(p)],check=True)
 for _ in range(2):subprocess.run([sys.executable,str(root/'tools/patch_stream_human_mouse_output.py'),str(p)],check=True)
 t=p.read_text(encoding='utf-8');py_compile.compile(str(p),doraise=True)
 for x in ('def _light_mouse(','HCFG|%d','HPAUSE|%d','HMOVE|%d','HRANDOM|%d','elif op in ("RMOUSE", "MOVETO")','ARM human mouse rejected'):
  assert x in t
 assert 'if lo<0 or hi<0 or hi<lo: raise ValueError("invalid mouse range")' in t
 assert 'arm27=ok' in t
print('Pico Phase 3 dispatch: exact profile fields, no hidden range swap, ARM 2.7 capability required')
