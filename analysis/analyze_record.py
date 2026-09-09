# Record Being Edited analysis - stop/start snap-back (code64)
import re, json, statistics

raw = open('/data/record-stop-start.txt','rb').read().decode('utf-16')  # handles BOM
lines = [l.strip() for l in raw.splitlines() if l.strip()]

t = 0
events = []
unknown = {}
for l in lines:
    m = re.match(r'^Delay : (\d+) ms$', l)
    if m: t += int(m.group(1)); continue
    m = re.match(r'^Mouse Position : X:(\d+) Y:(\d+)$', l)
    if m: events.append(('pos', t, int(m.group(1)), int(m.group(2)))); continue
    m = re.match(r'^(Key Down|Key Up) : (.+)$', l)
    if m: events.append(('key', t, m.group(2), m.group(1))); continue
    m = re.match(r'^Mouse Event : (.+)$', l)
    if m: events.append(('mevt', t, m.group(1))); continue
    unknown[l] = unknown.get(l, 0) + 1

print('total lines:', len(lines), '| events:', len(events), '| duration: %.1f s' % (t/1000))
print('unknown lines:', unknown if unknown else 'none')

keys = [e for e in events if e[0]=='key']
mevts = [e for e in events if e[0]=='mevt']
poss  = [e for e in events if e[0]=='pos']
print('key events:', len(keys), '| mouse events (clicks etc):', len(mevts), '| positions:', len(poss))
from collections import Counter
print('key histogram:', Counter((e[2],e[3]) for e in keys))
if mevts: print('mouse event histogram:', Counter(e[2] for e in mevts))

# region from plan.txt: RMOUSE region=1301,0,378,1049 -> x in [1301,1679], y in [0,1049]
RX0, RY0, RW, RH = 1301, 0, 378, 1049
def in_region(x,y): return RX0 <= x <= RX0+RW and RY0 <= y <= RY0+RH
inside = sum(1 for e in poss if in_region(e[2],e[3]))
print('positions inside plan region: %d/%d (%.1f%%)' % (inside, len(poss), 100*inside/max(1,len(poss))))

# Num Lock down = GP4 toggles (start/stop). Scroll Lock = pause.
nl = [e for e in events if e[0]=='key' and e[2]=='Num Lock' and e[3]=='Key Down']
sl = [e for e in events if e[0]=='key' and e[2]=='Scroll Lock' and e[3]=='Key Down']
print('Num Lock downs (toggles):', len(nl), '| Scroll Lock downs (pause):', len(sl))

def dist(a,b): return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

# For each Num Lock toggle: last pos strictly before, first pos at/after, and next few
print('\n=== around every Num Lock toggle (start/stop) ===')
toggle_rows = []
for i, e in enumerate(nl):
    tt = e[1]
    before = [p for p in poss if p[1] < tt]
    after  = [p for p in poss if p[1] >= tt]
    pb = before[-1] if before else None
    pa = after[0] if after else None
    row = {'i': i+1, 't_s': round(tt/1000,2)}
    if pb: row['before'] = (pb[2], pb[3]); row['before_t_s'] = round(pb[1]/1000,2)
    if pa: row['after']  = (pa[2], pa[3]); row['after_t_s']  = round(pa[1]/1000,2)
    if pb and pa:
        row['jump_px'] = round(dist((pb[2],pb[3]),(pa[2],pa[3])),1)
        row['dt_ms'] = pa[1]-pb[1]
        row['after_in_region'] = in_region(pa[2],pa[3])
    # first 6 positions after the toggle with per-step distances
    steps = []
    for j in range(min(6, len(after))):
        p = after[j]
        d = dist((after[j-1][2],after[j-1][3]),(p[2],p[3])) if j>0 else None
        steps.append({'t':round(p[1]/1000,2),'x':p[2],'y':p[3],'step':(round(d,1) if d is not None else None)})
    row['first_moves'] = steps
    toggle_rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

# teleport scan during whole record: consecutive positions >400px within <100ms
tele = []
for a,b in zip(poss, poss[1:]):
    d = dist((a[2],a[3]),(b[2],b[3])); dt = b[1]-a[1]
    if d > 400 and dt < 100:
        tele.append({'t_s':round(a[1]/1000,2),'from':(a[2],a[3]),'to':(b[2],b[3]),'d_px':round(d,1),'dt_ms':dt})
print('\nteleports (>400px <100ms):', len(tele))
for x in tele[:30]: print(json.dumps(x, ensure_ascii=False))

# step-size stats during dense movement (plan running) - acceptance: median ~3px
seg = [dist((a[2],a[3]),(b[2],b[3])) for a,b in zip(poss,poss[1:]) if b[1]-a[1] <= 50 and dist((a[2],a[3]),(b[2],b[3]))>0]
if seg:
    seg_sorted = sorted(seg)
    print('\nstep px: median %.2f | p90 %.2f | max %.1f | n=%d' % (statistics.median(seg), seg_sorted[int(len(seg_sorted)*0.9)], max(seg), len(seg)))

# where does the cursor sit right after each start? cluster the after positions
print('\n=== distinct snap targets (first pos after toggle) ===')
cnt = Counter((r['after'][0]//25*25, r['after'][1]//25*25) for r in toggle_rows if 'after' in r)
for k,v in cnt.most_common(10): print('~(%d,%d) x%d' % (k[0],k[1],v))

json.dump({'toggles':toggle_rows,'teleports':tele,'counts':{'positions':len(poss),'keys':len(keys),'mevts':len(mevts)}}, open('/data/analysis/record_summary.json','w'), ensure_ascii=False, indent=1)
print('\nsaved /data/analysis/record_summary.json')
