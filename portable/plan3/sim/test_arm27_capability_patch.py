#!/usr/bin/env python3
from pathlib import Path
import py_compile,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[3]
ino=(root/'firmware/arm27/ams_board27.ino').read_text(encoding='utf-8')
assert 'OK|HVER|2.7.0|HMOUSE=1' in ino
assert 'if(!arm27_handle(g_line1)) handle(g_line1);' in ino
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'code.py';shutil.copyfile(root/'firmware/pico-light-guard-1.0.0/code.py',p)
 subprocess.run([sys.executable,str(root/'tools/patch_combined_runtime_output.py'),str(p)],check=True)
 subprocess.run([sys.executable,str(root/'tools/patch_stream_type_output.py'),str(p)],check=True)
 subprocess.run([sys.executable,str(root/'tools/patch_stream_human_mouse_output.py'),str(p)],check=True)
 for _ in range(2):subprocess.run([sys.executable,str(root/'tools/patch_stream_human_mouse_capability_output.py'),str(p)],check=True)
 t=p.read_text(encoding='utf-8');py_compile.compile(str(p),doraise=True)
 assert 'owner.arm.send("HVER",3)' in t
 assert 'ARM 2.7 human mouse capability required' in t
print('ARM 2.7 capability negotiation: fail closed before profile or movement')
