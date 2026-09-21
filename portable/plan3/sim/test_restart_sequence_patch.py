#!/usr/bin/env python3
from pathlib import Path
import py_compile, shutil, subprocess, sys, tempfile
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'code.py'; shutil.copyfile(root/'firmware/pico-light-guard-1.0.0/code.py',p)
 for script in ('patch_combined_runtime_output.py','patch_guard_key_diagnostics.py','patch_restart_route_output.py','patch_restart_sequence_output.py'):
  subprocess.run([sys.executable,str(root/'tools'/script),str(p)],check=True)
 text=p.read_text(encoding='utf-8'); py_compile.compile(str(p),doraise=True)
 for marker in ('restart_steps.txt','_restart_tick(self)','restart-before-desktop','restart-complete desktop-next','RUNFOR|','usb_connected'):
  assert marker in text
 assert text.index('_run_light_route(self, "restart_steps.txt")') < text.index('_run_light_route(self, name)',text.index('restart_steps.txt'))
print('Restart sequence patch: verified reboot -> optional Restart route -> Desktop, then a fresh cycle')
