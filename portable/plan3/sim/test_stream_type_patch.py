#!/usr/bin/env python3
from pathlib import Path
import py_compile,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'code.py'; shutil.copyfile(root/'firmware/pico-light-guard-1.0.0/code.py',p)
 subprocess.run([sys.executable,str(root/'tools/patch_combined_runtime_output.py'),str(p)],check=True)
 for _ in range(2): subprocess.run([sys.executable,str(root/'tools/patch_stream_type_output.py'),str(p)],check=True)
 t=p.read_text(encoding='utf-8'); py_compile.compile(str(p),doraise=True)
 for x in ('def _light_type(','def _type_char(','def _type_neighbor(','elif op == "TYPE":','STEP/TYPE chars=%d'):
  assert x in t
 assert 'plan_typing(' not in t[t.index('def _light_type('):t.index('def _run_light_route')]
 assert 'text=%s' not in t
print('streaming TYPE: inclusive timing, pauses, typo/correction, no text logging')
