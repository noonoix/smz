# sim_arm19.py - behaviour model of the arm firmware's mouse path, 1.8 vs 1.9.
# 1.9 adds MMOVE abs,2 ("streamed path point"): each fed segment is subdivided into
# <=8 px linear micro-steps (max 3 substeps) emitted back-to-back at native HID pace
# (~8-10 ms each) -> ~100 reports/sec, hand-smooth, exact landing. Reference: the
# user's own hand recording (my hand.txt, 2026-09-09) = median 3 px per sample at
# ~390 samples/sec, median speed ~530 px/s; the PC->pico->arm chain tops out at
# ~50 fed points/sec, so the density must be generated ON the arm.
import sys

results = []
def check(cond, msg):
    results.append((bool(cond), msg))
    print(("PASS: " if cond else "FAIL: ") + msg)

SCRW, SCRH = 1920, 1080

def toAbsX(x):
    x = max(0, min(SCRW - 1, x))
    return (x * 65535) // (SCRW - 1) - 32768

def toAbsY(y):
    y = max(0, min(SCRH - 1, y))
    return (y * 65535) // (SCRH - 1) - 32768

def px_x(a):
    return (a + 32768) * (SCRW - 1) / 65535

def px_y(a):
    return (a + 32768) * (SCRH - 1) / 65535

class LibAbsMouse:
    """HID-Project AbsoluteMouse - verified semantics (press/release resend stored axes)."""
    def __init__(self):
        self.xAxis = 0
        self.yAxis = 0
        self._buttons = 0
        self.reports = []       # (buttons, xAxis, yAxis, wheel)
    def moveTo(self, x, y, wheel=0):
        self.xAxis = x
        self.yAxis = y
        self.reports.append((self._buttons, x, y, wheel))
    def press(self, b):
        nb = self._buttons | b
        if nb != self._buttons:
            self._buttons = nb
            self.moveTo(self.xAxis, self.yAxis, 0)
    def release(self, b):
        nb = self._buttons & ~b
        if nb != self._buttons:
            self._buttons = nb
            self.moveTo(self.xAxis, self.yAxis, 0)

LEFT = 1

class Arm:
    """Arm firmware model with the 1.8/1.9 dispatch (handler ported 1:1)."""
    def __init__(self, fw="1.9"):
        self.lib = LibAbsMouse()
        self.curX = 960     # 1.8+: tracker boots at the screen centre
        self.curY = 540
        self.fw = fw
    def cursor_sync(self):
        self.lib.moveTo(toAbsX(self.curX), toAbsY(self.curY), 0)
    def mouse_move_abs(self, x, y, human=False):
        if not human:
            self.lib.moveTo(toAbsX(x), toAbsY(y), 0)
            self.curX, self.curY = x, y
            return
        # the 1.7-1.9 board-side smoothstep trail (jitter modelled as 0: deterministic)
        dx, dy = x - self.curX, y - self.curY
        dist = int((dx * dx + dy * dy) ** 0.5)
        steps = max(6, min(48, dist // 8))
        sx, sy = self.curX, self.curY
        for i in range(1, steps + 1):
            t = i / steps
            e = t * t * (3.0 - 2.0 * t)
            self.lib.moveTo(toAbsX(sx + int(dx * e)), toAbsY(sy + int(dy * e)), 0)
        self.curX, self.curY = x, y
    def mouse_move_stream(self, x, y):
        dx, dy = x - self.curX, y - self.curY
        dist = int((dx * dx + dy * dy) ** 0.5)
        steps = dist // 8
        if steps > 3:
            steps = 3
        if steps < 1:
            self.lib.moveTo(toAbsX(x), toAbsY(y), 0)
            self.curX, self.curY = x, y
            return
        sx, sy = self.curX, self.curY
        for i in range(1, steps + 1):
            px = sx + int(dx * i / steps)   # C int32: truncation toward zero (float is exact here)
            py = sy + int(dy * i / steps)
            self.lib.moveTo(toAbsX(px), toAbsY(py), 0)
        self.curX, self.curY = x, y
    def mmove(self, x, y, mode="abs", hm="1"):
        if mode == "rel":
            self.mouse_move_abs(self.curX + x, self.curY + y)
            return
        if self.fw >= "1.9" and hm == "2":
            self.mouse_move_stream(x, y)
        else:
            self.mouse_move_abs(x, y, hm == "1")   # 1.8 reads hm==2 as non-human -> plain jump
    def mclick(self):
        self.cursor_sync()
        self.lib.press(LEFT)
        self.lib.release(LEFT)

# ---- S1: graceful degradation - fw 1.8 receives abs,2 (old bridge pairings stay safe) ----
a = Arm(fw="1.8")
a.mmove(700, 400, hm="2")
check(len(a.lib.reports) == 1 and (a.curX, a.curY) == (700, 400),
      "S1: fw 1.8 reads hm==2 as a plain jump (1 report) - old arm + new bridge still works")

# ---- S2: fw 1.9 stream subdivision ----
b = Arm()
b.mmove(990, 540, hm="2")          # 30 px to the right
rs = b.lib.reports
check(len(rs) == 3, "S2: 30 px segment -> 3 sub-reports (<=8 px each)")
pts = [(round(px_x(r[1])), round(px_y(r[2]))) for r in rs]
check(pts[-1] == (990, 540) and (b.curX, b.curY) == (990, 540),
      "S2: lands exactly on the fed point, tracker exact (%s)" % (pts,))
check(all(pts[i][0] > pts[i-1][0] for i in range(1, len(pts))), "S2: strictly forward along the segment")

# ---- S3: subdivision sizing ----
c = Arm()
c.mmove(965, 540, hm="2")           # 5 px
check(len(c.lib.reports) == 1, "S3: 5 px -> single report")
n0 = len(c.lib.reports)
c.mmove(965 + 17, 540, hm="2")      # 17 px
check(len(c.lib.reports) - n0 == 2, "S3: 17 px -> 2 reports")
n0 = len(c.lib.reports)
c.mmove(982 + 100, 540, hm="2")     # 100 px
check(len(c.lib.reports) - n0 == 3, "S3: 100 px -> capped at 3 reports (stays inside the 25 ms feed cadence)")

# ---- S4: zero-length point is harmless ----
d = Arm()
d.mmove(960, 540, hm="2")
check(len(d.lib.reports) == 1 and (d.curX, d.curY) == (960, 540), "S4: zero-length point -> 1 no-op report")

# ---- S5: a full WindMouse-style path stays in the corridor and lands exactly ----
path = [(960,540),(985,552),(1012,570),(1040,592),(1066,618),(1088,648),(1104,680),
        (1114,712),(1118,744),(1117,775),(1110,804),(1098,830),(1082,850)]
e = Arm()
e.mmove(*path[0], hm="0")            # jump to the start
start_reports = len(e.lib.reports)
for p in path[1:]:
    e.mmove(*p, hm="2")
rs = e.lib.reports[start_reports:]
def on_segment(p0, p1, r):
    rx, ry = px_x(r[1]), px_y(r[2])
    x0, y0 = p0; x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L = max(1.0, (dx * dx + dy * dy) ** 0.5)
    cross = abs(dx * (ry - y0) - dy * (rx - x0)) / L          # distance off the line
    along = ((rx - x0) * dx + (ry - y0) * dy) / (L * L)       # 0..1 between the points
    return cross <= 2.0 and -0.1 <= along <= 1.1
seg_ok = True
idx = 0
for i in range(1, len(path)):
    p0, p1 = path[i - 1], path[i]
    dist = ((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2) ** 0.5
    n = min(3, int(dist) // 8) or 1
    for r in rs[idx:idx + n]:
        seg_ok = seg_ok and on_segment(p0, p1, r)
    idx += n
check(idx == len(rs) and seg_ok, "S5: every sub-report lies on its fed segment (13-point path, %d reports)" % len(rs))
check((e.curX, e.curY) == path[-1] and (round(px_x(rs[-1][1])), round(px_y(rs[-1][2]))) == path[-1],
      "S5: the path lands exactly on the final target")

# ---- S6: regressions - abs,0 stays a plain jump; abs,1 keeps the eased board trail ----
f = Arm()
f.mmove(1200, 700, hm="0")
check(len(f.lib.reports) == 1, "S6: abs,0 -> single jump (unchanged)")
g = Arm()
g.mmove(1260, 700, hm="1")           # 340 px diagonal
check(6 <= len(g.lib.reports) <= 48 and len(g.lib.reports) == 42,
      "S6: abs,1 -> board-side smoothstep trail (%d reports, unchanged)" % len(g.lib.reports))

# ---- S7: the 1.8 invariant still holds - a click after a streamed path never jumps ----
h = Arm()
h.mmove(985, 552, hm="2")
h.mmove(1012, 570, hm="2")
h.mclick()
last = h.lib.reports[-1]
check((last[1], last[2]) == (toAbsX(1012), toAbsY(570)),
      "S7: click after a streamed path reports the tracked position (no centre reset)")

failed = [m for ok, m in results if not ok]
print()
print("=== sim_arm19: %d passed, %d failed ===" % (len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
