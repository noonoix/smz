# sim_arm18.py - behaviour model of the arm firmware's mouse path, 1.7 vs 1.8.
# The HID-Project AbsoluteMouse model below is verified line-by-line from
# src/HID-APIs/AbsoluteMouseAPI.hpp:
#   moveTo(x,y,w): stores xAxis/yAxis, sends a report with THOSE axes + wheel
#   move(x,y,w):   relative - moveTo(qadd16(xAxis,x), qadd16(yAxis,y), w)
#   press/release: buttons() resends a report with the STORED axes (wheel 0)
#   library boots with xAxis=yAxis=0, and on that signed axis 0 = screen CENTRE.
# The firmware handlers are ported 1:1 from ams_board17.ino / ams_board18.ino.
import sys

results = []
def check(cond, msg):
    results.append((bool(cond), msg))
    print(("PASS: " if cond else "FAIL: ") + msg)

SCRW, SCRH = 1920, 1080

def qadd16(base, inc):
    r = base + inc
    return max(-32768, min(32767, r))

def toAbsX(x):
    x = max(0, min(SCRW - 1, x))
    return (x * 65535) // (SCRW - 1) - 32768      # C++ int32 truncation == // for positives

def toAbsY(y):
    y = max(0, min(SCRH - 1, y))
    return (y * 65535) // (SCRH - 1) - 32768

def axis_to_px_x(a):
    return (a + 32768) * (SCRW - 1) / 65535

def axis_to_px_y(a):
    return (a + 32768) * (SCRH - 1) / 65535

class LibAbsMouse:
    """HID-Project AbsoluteMouse - verified semantics."""
    def __init__(self):
        self.xAxis = 0          # boots to 0 -> signed 0 = screen CENTRE
        self.yAxis = 0
        self._buttons = 0
        self.reports = []       # (buttons, xAxis, yAxis, wheel)
    def moveTo(self, x, y, wheel=0):
        self.xAxis = x
        self.yAxis = y
        self.reports.append((self._buttons, x, y, wheel))
    def move(self, x, y, wheel=0):
        self.moveTo(qadd16(self.xAxis, x), qadd16(self.yAxis, y), wheel)
    def press(self, b):
        nb = self._buttons | b
        if nb != self._buttons:
            self._buttons = nb
            self.moveTo(self.xAxis, self.yAxis, 0)   # RESENDS the stored axes
    def release(self, b):
        nb = self._buttons & ~b
        if nb != self._buttons:
            self._buttons = nb
            self.moveTo(self.xAxis, self.yAxis, 0)

LEFT = 1

class Arm17:
    """ams_board17.ino mouse handlers, 1:1."""
    def __init__(self):
        self.lib = LibAbsMouse()
        self.curX = 0           # 1.7: tracker boots at the top-left CORNER
        self.curY = 0
    def mouse_move_abs(self, x, y, human=False):
        self.lib.moveTo(toAbsX(x), toAbsY(y), 0)
        self.curX, self.curY = x, y
    def mmove(self, x, y, mode="abs"):
        if mode == "rel":
            self.lib.move(max(-127, min(127, x)), max(-127, min(127, y)), 0)   # AXIS units!
            self.curX += x; self.curY += y
        else:
            self.mouse_move_abs(x, y)
    def mclick(self):
        self.lib.press(LEFT); self.lib.release(LEFT)
    def mdown(self):
        self.lib.press(LEFT)
    def mwheel(self, d):
        self.lib.move(0, 0, d)
    def mdrag(self, dx, dy):
        self.lib.press(LEFT)
        self.lib.move(max(-127, min(127, dx)), max(-127, min(127, dy)), 0)
        self.lib.release(LEFT)

class Arm18:
    """ams_board18.ino mouse handlers, 1:1 (cursor_sync + tracker boots at centre)."""
    def __init__(self):
        self.lib = LibAbsMouse()
        self.curX = 960         # 1.8: tracker boots at the screen CENTRE (Windows' boot cursor)
        self.curY = 540
    def cursor_sync(self):
        self.lib.moveTo(toAbsX(self.curX), toAbsY(self.curY), 0)
    def mouse_move_abs(self, x, y, human=False):
        self.lib.moveTo(toAbsX(x), toAbsY(y), 0)
        self.curX, self.curY = x, y
    def mmove(self, x, y, mode="abs"):
        if mode == "rel":
            self.mouse_move_abs(self.curX + x, self.curY + y)   # PIXEL delta via tracker
        else:
            self.mouse_move_abs(x, y)
    def mclick(self):
        self.cursor_sync()
        self.lib.press(LEFT); self.lib.release(LEFT)
    def mdown(self):
        self.cursor_sync()
        self.lib.press(LEFT)
    def mwheel(self, d):
        self.lib.moveTo(toAbsX(self.curX), toAbsY(self.curY), d)
    def mdrag(self, dx, dy):
        self.cursor_sync()
        self.lib.press(LEFT)
        self.mouse_move_abs(self.curX + dx, self.curY + dy)
        self.lib.release(LEFT)

# ---- S1: the bug - boot click/scroll without any prior move ----
a = Arm17();  a.mclick()
rep = a.lib.reports[-1]
check((rep[1], rep[2]) == (0, 0), "S1: 1.7 boot click resends the library boot axes (0,0) = CENTRE (the bug)")
check((rep[1], rep[2]) != (toAbsX(a.curX), toAbsY(a.curY)),
      "S1: 1.7 tracker (corner) and library (centre) disagree - the two were never synced")
a = Arm17();  a.mwheel(-1)
rep = a.lib.reports[-1]
check((rep[1], rep[2]) == (0, 0) and rep[3] == -1,
      "S1: 1.7 boot scroll sends axes (0,0) = CENTRE + wheel -1 (cursor jumps, then scrolls there)")

b = Arm18();  b.mclick()
rep = b.lib.reports[-1]
check((rep[1], rep[2]) == (toAbsX(960), toAbsY(540)),
      "S1: 1.8 boot click reports the TRACKED position (centre = Windows' boot cursor)")

# ---- S2: no regression - click/scroll after a board-driven move ----
a = Arm17(); a.mmove(300, 200); a.mclick()
b = Arm18(); b.mmove(300, 200); b.mclick()
check(a.lib.reports[-1][1:3] == b.lib.reports[-1][1:3] == (toAbsX(300), toAbsY(200)),
      "S2: click-after-move identical in both (tracked position)")
a = Arm17(); a.mmove(300, 200); a.mwheel(-1)
b = Arm18(); b.mmove(300, 200); b.mwheel(-1)
check(b.lib.reports[-1] == (0, toAbsX(300), toAbsY(200), -1),
      "S2: 1.8 scroll keeps the cursor at the tracked position and passes the wheel delta")

# ---- S3: the 1.8 invariant - after EVERY op, the last report carries the tracked position ----
b = Arm18()
def last_axes_ok():
    r = b.lib.reports[-1]
    return (r[1], r[2]) == (toAbsX(b.curX), toAbsY(b.curY))
oks = []
b.mclick();            oks.append(last_axes_ok())   # boot click (centre, intentional)
b.mmove(700, 800);     oks.append(last_axes_ok())   # board-driven move
b.mclick();            oks.append(last_axes_ok())   # click after move
b.mwheel(1);           oks.append(last_axes_ok())   # scroll
b.mdown();             oks.append(last_axes_ok())   # press
b.mwheel(-1);          oks.append(last_axes_ok())   # scroll while held
check(all(oks), "S3: 1.8 invariant - every op's last report carries the tracked position")

# ---- S4: rel-MMOVE - 1.7 moved AXIS units (~7px per 100px!), 1.8 moves pixels ----
a = Arm17(); a.mmove(300, 200); a.mmove(100, 50, mode="rel")
land17 = (axis_to_px_x(a.lib.reports[-1][1]), axis_to_px_y(a.lib.reports[-1][2]))
check(abs(land17[0] - 300) < 8 and abs(land17[1] - 200) < 8,
      "S4: 1.7 rel(100,50) barely moved (landed %.0f,%.0f - axis-unit bug)" % land17)
b = Arm18(); b.mmove(300, 200); b.mmove(100, 50, mode="rel")
land18 = (axis_to_px_x(b.lib.reports[-1][1]), axis_to_px_y(b.lib.reports[-1][2]))
check(abs(land18[0] - 400) < 3 and abs(land18[1] - 250) < 3,
      "S4: 1.8 rel(100,50) lands at (400,250) - true pixel delta")

# ---- S5: MDRAG - same pixel-delta fix + tracker stays in sync ----
b = Arm18(); b.mmove(300, 200); b.mdrag(200, 100)
check((b.curX, b.curY) == (500, 300), "S5: 1.8 drag updates the tracker to (500,300)")
check(b.lib.reports[-1][0] == 0 and (b.lib.reports[-1][1], b.lib.reports[-1][2]) == (toAbsX(500), toAbsY(300)),
      "S5: 1.8 drag release reports the drop position")
pressed = [r for r in b.lib.reports if r[0] & LEFT]
check(pressed and (pressed[0][1], pressed[0][2]) == (toAbsX(300), toAbsY(200)),
      "S5: 1.8 drag press reports the pickup position (not centre)")

# ---- S6: wheel delta sign passes through unchanged ----
b = Arm18(); b.mwheel(-1)
check(b.lib.reports[-1][3] == -1, "S6: wheel delta passes through (-1 = down)")

failed = [m for ok, m in results if not ok]
print()
print("=== sim_arm18: %d passed, %d failed ===" % (len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
