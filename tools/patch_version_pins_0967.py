#!/usr/bin/env python3
"""Cut Classroom Studio 0.9.67 while preserving accepted hardware/runtime pins."""
from pathlib import Path
import re,sys
APP_OLD='0.9.66'; APP='0.9.67'; BUNDLE='0.9.64f'
CSPROJ=Path('ams-shell/src/Ams.UI/Ams.UI.csproj')
VM=Path('ams-shell/src/Ams.UI/ViewModels/MainViewModel.cs')
RUNNER=Path('tests/TestRunner.cs')

def replace_checked(path,old,new,minimum=1):
 text=path.read_text(encoding='utf-8')
 if new in text and old not in text: print('ok   already patched:',path); return
 hits=text.count(old)
 if hits<minimum: raise RuntimeError(f'{path}: expected at least {minimum} x {old!r}, found {hits}')
 path.write_text(text.replace(old,new),encoding='utf-8'); print('edit',path,hits)
try:
 replace_checked(CSPROJ,'<Version>0.9.66</Version>','<Version>0.9.67</Version>')
 replace_checked(VM,'Classroom Studio v0.9.66','Classroom Studio v0.9.67')
 replace_checked(RUNNER,'<Version>0.9.66</Version>','<Version>0.9.67</Version>',20)
 replace_checked(RUNNER,'Classroom Studio v0.9.66','Classroom Studio v0.9.67',15)
 replace_checked(RUNNER,'csproj version is 0.9.66','csproj version is 0.9.67',2)
 replace_checked(RUNNER,'        var curMinor = 66;','        var curMinor = 67;')
except RuntimeError as exc:
 print('FAIL:',exc); sys.exit(1)
runner=RUNNER.read_text(encoding='utf-8')
if '<Version>0.9.67</Version>' not in CSPROJ.read_text(encoding='utf-8'): sys.exit('FAIL: csproj pin')
if 'Classroom Studio v0.9.67' not in VM.read_text(encoding='utf-8'): sys.exit('FAIL: banner pin')
if '        var curMinor = 67;' not in runner or '        var curBundleMinor = 64;' not in runner: sys.exit('FAIL: meta pins')
app,bundle=set(),set()
for line in runner.splitlines():
 is_bundle='BundleVersion' in line
 if '<Version>0.9.' not in line and 'Classroom Studio v0.9.' not in line and not is_bundle: continue
 for m in re.finditer(r'0\.9\.(\d+)',line):
  i=m.start(); label=i>0 and line[i-1]=='v' and m.end()<len(line) and line[m.end()]==':'
  if not label: (bundle if is_bundle else app).add(int(m.group(1)))
if app!={67} or bundle!={64}: sys.exit(f'FAIL: pin families app={sorted(app)} bundle={sorted(bundle)}')
print('PASS: app 0.9.67; Pico bundle 0.9.64f; Pro Micro accepted 2.6.1')
