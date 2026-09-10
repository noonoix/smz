#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/patch_version_pins_0965.py'); s=p.read_text(encoding='utf-8'); n=s.count('0.9.64b')
if n<3: raise SystemExit(f'ERROR: expected b references, found {n}')
s=s.replace('0.9.64b','0.9.64f').replace('firmware template is untouched','firmware template stays on the accepted 0.9.64f line').replace('firmware untouched','firmware stays on the accepted 0.9.64f line')
p.write_text(s,encoding='utf-8',newline=''); print(f'PASS release patch updated ({n})')
