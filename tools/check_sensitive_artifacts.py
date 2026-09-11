#!/usr/bin/env python3
from pathlib import Path
import re, subprocess, sys
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
files=subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()
name_rules=[re.compile(r'(^|/)(ams_key\.(json|h))$',re.I),re.compile(r'(^|/).*(flash|eeprom).*(backup|dump)',re.I),re.compile(r'(^|/).*(backup|dump).*(flash|eeprom)',re.I),re.compile(r'(^|/).*(personal|real).+\.hex$',re.I)]
text_rules=[('private key',re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----')),('GitHub token',re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}')),('generic secret assignment',re.compile(r'''(?i)(password|api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*["'][^"']{12,}["']'''))]
allow_ext={'.md','.txt','.py','.cs','.yml','.yaml','.json','.xml','.props','.targets','.ps1','.sh','.ino','.h','.cpp','.js','.ts'}
errors=[]
for rel in files:
 if any(r.search(rel) for r in name_rules): errors.append(f'forbidden artifact name: {rel}');continue
 p=root/rel
 if p.suffix.lower() not in allow_ext or not p.is_file() or p.stat().st_size>2_000_000: continue
 try:s=p.read_text(encoding='utf-8')
 except UnicodeDecodeError:continue
 for label,rx in text_rules:
  if rx.search(s):errors.append(f'{label}: {rel}')
if errors:
 print('\n'.join('ERROR: '+x for x in errors));sys.exit(1)
print(f'SENSITIVE GUARD OK: {len(files)} tracked files checked')
