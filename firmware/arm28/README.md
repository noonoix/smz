# Classroom Studio ARM 2.8 — portable relative mouse

This is the exact ARM 2.7 source currently used on the Pro Micro, with one
focused change: `MMOVE|dx,dy,rel,2` now emits genuine relative HID reports.
Windows applies each delta to the cursor's real current position, so no bridge,
`CURSOR|x,y`, absolute reset, or centre jump is required.

ARM 2.8 uses one Arduino-core `PortableMouse` interface for movement, buttons and
wheel. Existing `MMOVE`, `HMOVE`, `HRANDOM`, sound, framed UART, encrypted USB,
HOSTUSB, HALT and button behavior remain available. `HSETCUR` still aligns the
virtual ledger when an optional host-assisted workflow uses it; the fully
portable path does not call it.

Keep all source files, including `portable_relative_mouse.h`, in one Arduino sketch folder. Copy your existing private
`ams_key.h` beside them (never commit it); `ams_key.example.h` is only a template.
Open `ams_board28.ino`, select the same Classroom Studio Board / Pro Micro
5V 16 MHz profile used for ARM 2.7, compile, and upload. The verified build uses
28,594 of 28,672 bytes, so it fits the normal Caterina/Leonardo bootloader profile;
ISP remains optional.
