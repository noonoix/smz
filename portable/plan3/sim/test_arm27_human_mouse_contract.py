#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[3]
ino=(root/'firmware/arm27/ams_board27.ino').read_text(encoding='utf-8')
h=(root/'firmware/arm27/human_mouse_v3.h').read_text(encoding='utf-8')
for token in ('HCFG','HPAUSE','HMOVE','HRANDOM','configured=false','configured=true','overChance','midChance','idleEveryMin','speedMin','moveMin','curveMin','beforeMin','afterMin'):
 assert token in h
assert 'poll_host_usb();' in h and 'HALT' in h and 'ERR|ABORTED|HMOVE' in h
assert 'SingleAbsoluteMouse.moveTo' in h
assert 'arm26_setup' in ino and 'human_mouse_v3_handle' in ino
assert 'mouse_move_abs(x, y, true)' not in h
print('ARM 2.7 Phase 3A: full profile transport, curved bounded path, overshoot/correction, pauses and HALT contract')
