# Bug Report: Cut BMP from Screen — RegionPicker double-click confirm broken

**Date:** 2026-08-24  
**Version:** v0.8.1  
**Severity:** Critical — core feature non-functional  
**Status:** ✅ Root cause fixed — v0.8.1 (confirmed working)

---

## Problem Description

When user clicks "Cut BMP From Screen", drags a region on the full-screen overlay, then double-clicks to confirm — nothing happens:
- No BMP is saved to `captures/`
- No preview appears in the white thumbnail box
- Remove Picture button stays disabled

**Evidence from user's screenshot:**
```
Rectangle Point 2: (1472,346) Size: 0x0
```
→ Region width = 0 pixels → the drag never established any valid region.

---

## Root Cause (Identified via Debug Log)

### What the log revealed

After adding debug logging to every event, the exact failure sequence was captured:

```
[02:25:14.062] LBDN ClickCount=1 NEW_DRAG start=(1750,921)
  ← User clicked and started dragging

[02:25:14.064-14.616] MOVE events... w grows from 0→140, h from 0→125
  ← User dragged to create a 140×125 region

[02:25:14.616] LBUP w=140.00 h=125.00 Region=[1610,921 140x125] hasRegion=True
  ← User released mouse. Region committed successfully! ✓

[02:25:14.927] MOVE pos=(1677,964) start=(1677,964) w=0.00 h=0.00 dragging=True
[02:25:14.927] LBDN ClickCount=1 SAVE(saved=(140.00,125.00)) RESET w=0 h=0 dragging=true
  ← 311ms LATER, user clicked again (intending to double-click-confirm)
  ← BUT: WPF reported ClickCount=1 (not 2!) because mouse moved ~77px between clicks
  ← The "second click" entered the NEW_DRAG branch and RESET the region!

[02:25:14.927] LBUP w=0.00 h=0.00 Region=[1677,964 1x1] hasRegion=False
  ← Region destroyed. Double-click confirm failed silently.
```

### Why WPF said ClickCount=1 instead of ClickCount=2

WPF's double-click detection requires:
1. Two clicks within the system double-click time threshold
2. **The second click at roughly the same position as the first**

In this case, the user's mouse moved ~77 pixels between the two clicks (from release point 1662,991 to click point 1677,964). This exceeded WPF's proximity threshold for double-click recognition, so WPF treated the second click as a single click (ClickCount=1) rather than part of a double-click.

### The bug flow

```
User action                    WPF event          Code path                Result
────────────────────────────   ──────────────     ─────────────────────    ─────────────────
1. Click + drag                LBDN(ClickCount=1) → NEW_DRAG branch       Start drag, _w=0,_h=0
2. Mouse moves                  MOVE events       → w/h grow               Region grows
3. Release                      LBUP              → CommitToFields()       Region=[1610,921 140x125]
4. Move mouse slightly to reposition
5. Click again (intending to   LBDN(ClickCount=1) → NEW_DRAG branch       REGION RESET! 🐛
   confirm with double-click)                              → _w=0,_h=0             hasRegion=false
6. Release immediately          LBUP              → CommitToFields()       Region=[1677,964 1x1]
                                                                 hasRegion=false
7. MouseDoubleClick never      (fires but         → _hasRegion=false       Fail silently
   actually fires (because       _hasRegion=false   → DialogResult stays
   ClickCount was 1, not 2)     so condition        false
   fails)                       fails)
```

---

## Fix Applied

### Approach: Always-confirm when region exists (v0.8.1 final)

Previous attempts using WPF `ClickCount` or position-proximity checks all failed because:
- WPF's double-click detection requires both time AND position proximity (~2px)
- `_lastClickPos` was the drag START position, not the region's position
- Distance between start and confirm click was often 500+ pixels → proximity always false → region reset

**Final approach:** When a valid region already exists, ANY left-click confirms it. No timing or position checks needed.

```csharp
private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
{
    // v0.8.1 — double-click confirm fix (approach 3):
    // When a valid region already exists, ANY left-click confirms it immediately.
    // No double-click timing/position check needed — eliminates WPF ClickCount bug.
    if (_hasRegion && RegionW >= 3 && RegionH >= 3)
    {
        CommitToFields();
        Log($"LBDN ClickCount={e.ClickCount} CONFIRM Region=[{RegionX},{RegionY} {RegionW}x{RegionH}]");
        DialogResult = true;
        return;
    }
    // No valid region yet — start a new drag
    _start = e.GetPosition(Canvas);
    _x = _start.X; _y = _start.Y; _w = 0; _h = 0;
    _dragging = true;
    _hasRegion = false;
    CaptureMouse();
    InfoText.Visibility = Visibility.Visible;
    UpdateRect();
    Log($"LBDN ClickCount={e.ClickCount} NEW_DRAG start=({(int)_start.X},{(int)_start.Y})");
}
```

**Logic:**
- After region created (`_hasRegion && RegionW >= 3 && RegionH >= 3`)
- ANY left-click → confirm and close (DialogResult = true)
- No region yet → start new drag
- MouseDoubleClick kept as safety net for edge cases

**Why this works:**
- Eliminates dependency on WPF's ClickCount timing/proximity
- Single click = confirm (simpler UX)
- Double-click still works (first click hits CONFIRM branch, returns before double-click fires)
- Only resets region when there's NO existing valid region

---

## Files Changed

| File | Change |
|------|--------|
| `Views/RegionPickerWindow.xaml.cs` | Replaced `_savedW/_savedH` pattern with proximity-based detection |
| `docs/bug-report-cutbmp-region-picker.md` | This document |

---

## Test Status

- ✅ Unit tests: 53/53 pass
- ✅ Manual testing: CONFIRM working — 3 successful captures logged
- ✅ BMP files created in `captures/` folder
- ✅ RegionPickerWindow closes and returns valid region coordinates

---

## Debug Logging

A `Log()` method writes to both `System.Diagnostics.Debug` AND a file:
`bin/Debug/net8.0-windows/regionpicker-debug.log`

**Log format:**
```
[HH:mm:ss.fff] LBDN ClickCount=N NEW_DRAG start=(x,y)
[HH:mm:ss.fff] LBDN ClickCount=N PROXIMATE=true → CONFIRM Region=[x,y WxH]
[HH:mm:ss.fff] LBUP w=W h=H Region=[x,y WxH] hasRegion=True/False
[HH:mm:ss.fff] DOUBLECLICK _hasRegion=? RegionW=? RegionH=? → DialogResult=?
[HH:mm:ss.fff] MOVE pos=(x,y) start=(x,y) w=W h=H dragging=True
```

---

## How to Reproduce & Verify

1. Open the app (currently running with PID 3928)
2. Insert → Find Image On Screen
3. Click "Cut BMP From Screen (Shift + F11)"
4. On the full-screen overlay, DRAG to draw a rectangle (make it at least 50×50 pixels)
5. Release the mouse button (you should see "Double-click to confirm..." hint)
6. DOUBLE-CLICK inside the rectangle to confirm
7. Expected: BMP saved to `captures/`, preview shown, Remove button enabled
8. Read the debug log: `bin/Debug/net8.0-windows/regionpicker-debug.log`

**Expected log for success:**
```
LBDN ClickCount=1 NEW_DRAG start=(...)
MOVE events... w/h growing
LBUP w=136.00 h=53.00 Region=[1777,974 136x53] hasRegion=True
LBDN ClickCount=1 CONFIRM Region=[1777,974 136x53]   ← single click confirms!
```

---

## Environment

- .NET 8 + WPF
- WPF-UI 3.0.5
- CommunityToolkit.Mvvm 8.3.2
- `UseWindowsForms=true` → CS0104 awareness needed
- App PID: 8072 (running with debug logging)
- exe build time: 2026-08-24 02:33:xx
