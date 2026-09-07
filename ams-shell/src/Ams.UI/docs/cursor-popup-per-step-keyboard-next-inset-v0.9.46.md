# v0.9.46 — cursor-geometry popup close, per-step keyboard board, Next inset

## 1. Rail popup finally closes without a click

The v0.9.45 watcher still used WPF `IsMouseOver`. A `ContextMenu` is hosted in a separate
Popup/HWND and that state can remain stale until the next click — exactly matching the user's
observation that the submenu stayed open indefinitely.

The watcher now reads `System.Windows.Forms.Control.MousePosition` and compares the real screen
cursor with screen rectangles obtained from `PointToScreen` for both the rail host and the open
ContextMenu. After the cursor is outside both for three 120 ms ticks, the single state-machine
owner closes the popup. A visual disconnected during close is handled as outside.

## 2. Keyboard executor per step

The design is useful and safe when implemented as an override, not as a replacement for the
global rule. These four steps now expose `keyboardBoard = default | pico | promicro`:

- Keystroke
- Type Text
- Key Down
- Key Up

`default` preserves old plans and delegates to Options (`KBD_ON_ARM`). Explicit steps use a wire
envelope only understood/consumed by the Pico brain:

- `KBDPICO|<KTEXT/KCOMBO/KDOWN/KUP...>` — execute locally on Pico;
- `KBDARM|<...>` — forward this command to Pro Micro over UART.

Transport safety:

- connected Pico: receives the envelope and applies the per-step override;
- direct Pro Micro + `promicro`: app unwraps the envelope and sends the original firmware-1.6
  command, preserving compatibility;
- direct Pro Micro + `pico`: app stops with a clear error instead of sending an invalid command;
- DLY and CLIPBOARD pseudo commands remain PC-local.

This lets consecutive keyboard steps switch boards while the global Options choice remains the
fallback. It divides load without moving mouse commands: mouse/sound continue to belong to the
Pro Micro, while only keyboard work is selectable.

The exported `code.py` now consumes both envelopes before its existing keyboard handler and UART
forwarder, so the Pico firmware output supports the per-step decisions.

## 3. Next label inset

`# Next` remains a root-level sibling marker and the loop's red-vein endpoint. Only its summary
text receives a 12 px `SummaryInset`; numbering, actual depth, children and scope range remain
unchanged. This moves the label just inside the closing red cap without corrupting hierarchy.

## Validation

- v0.9.45 real test: 484 passed / 1 failed; the one failure was a stale v0.9.37 source-string
  assertion that did not include `loopHealed`. Product behavior was not failing; assertion fixed.
- Step 46: 15 textual Assert calls, 18 runtime assertions (four keyboard types are swept).
- Expected v0.9.46: **503 passed / 0 failed** (485 prior runtime assertions + 18).
- Total textual `Assert(` call sites: 457.
- C# balance: zero; XML parse: pass; U+FFFD: zero.
- Generated Pico code compiles in timed/once/forever and both global keyboard roles, with both
  per-step envelopes present.
