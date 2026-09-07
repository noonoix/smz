# AMS — Arduino Macro Studio (WPF shell v0.6)

Desktop macro studio for the AMS board (Arduino Pro Micro, encrypted serial HID,
firmware 1.6 — 28/28 acceptance tests passing).

## Stack
- **.NET 8 + WPF**, MVVM (`CommunityToolkit.Mvvm`), **WPF-UI 3.0.5** (NuGet — hyphenated!)
  (note: WPF-UI 3.0.5 has no ComboBox/CheckBox classes — those come from System.Windows.Controls)
- Plain `Window` with standard chrome (minimize / maximize / close) + **app icon** (`Resources/ams.ico`)
- Board transport: **Python sidecar** (`bridge/bridge.py` + `ams_serial.py`) — option B, §13.10.
  A native C# port (option A) is planned before v1.0 so no helper process exists (§13.11 stealth).
  The C# port must reproduce the four rules of §15.4: ascending counter · persistent
  RX buffer · resync after loss · command-proportional timeouts.

## Build & run
```powershell
cd src/Ams.UI
dotnet restore
dotnet build   # if MSB3021/MSB3027 (exe locked): taskkill /F /IM Ams.UI.exe, then build again
dotnet run
```
Requires the .NET 8 SDK + Python with `pyserial` (`pip install pyserial`).

## What works in v0.6 (new)
- **App icon** — exe icon + window title-bar icon (`Resources/ams.ico`)
- **White steps canvas** — the steps area is a light document on dark chrome
  (AMK-like, user request); rest of the app stays dark
- **Right-click context menu** on steps (AMK parity): Edit / Delete / Add Action ▸ (all 16 types)
  · Cut / Copy / Paste (step subtree, JSON-based) · Enable/Disable (Ctrl+D)
  · Disable All But This / Enable All But This · Batch Edit Delays
- **Drag & drop** — drag a step onto another: top quarter = insert before,
  bottom quarter = after, middle = drop into a container (For Loop / Find Image);
  dropping on empty space moves it to the root end
- **Import .amk for real** (File menu): runs the amk_toolkit decoder
  (`python amk_decoder.py file.amk --json … --imgdir …`) and maps the records onto
  the step model — verified against the toolkit's sample decodes (§9.2 table).
  Search pictures come along as extracted PNG paths. Else branches are imported
  as note comments (full If/Else modeling lands later). Decoder stderr is shown
  in the log if it fails. Toolkit folder is configurable in Tools → Options
- **Two new step types**: Open File / Program (PC-side `Start-Process`) and
  Play Script (.amk) — decoded and run recursively with the §17.5 cycle guard
  (call-stack set + max depth 4)

## Also in the shell (since v0.4/v0.5)
- **File**: New / Open / Save / Save As (`.amsj` JSON) · Generate Script (`.ps1`) · Exit
- **Edit**: Edit step (F2 / double-click) · Delete (Del) · Enable/Disable (Ctrl+D)
  · Move Up/Down (Alt+↑/↓) · Batch Edit Delays (set / multiply)
- **Insert** (16 step types): Mouse Click · Mouse Position · Mouse Scroll · Random Mouse Position
  · Keystroke · Type Text (keystrokes / clipboard / **sensitive**) · Key Down/Up · Delay · For Loop
  · **Wait For Sound** (WSND or armed TRGSND + Calibrate button) · **Find Image** (real PC-side
  template matching, GDI + NCC — no OpenCV) · Open File / Program · Play Script · Comment · Raw Command
- **Region Picker** (§5.5.12): full-screen overlay in Find Image / Random Mouse Position dialogs
- **Tools → Options**: COM port (AUTO default) · Python folder · AMK toolkit folder
- **Connect / Run / Stop**: encrypted handshake via the Python bridge; run engine walks the
  tree (loops, delays, DIS skip, sound windows, find-image vision, play-script recursion)
  and always sends HALT at the end

## Command syntax (verified against firmware 1.6)
`MCLICK|left,1` · `MMOVE|x,y,abs[,1]` · `MWHEEL|delta` · `KCOMBO|162+115` (decimal VK) ·
`KDOWN|vk` / `KUP|vk` · `KTEXT|hmin,hmax,text` (ASCII only → clipboard mode for non-Latin
or sensitive text) · `WSND|thr,minMs,timeoutMs` · `TRGSND|thr,minMs,timeoutMs,act,rMin,rMax,hMin,hMax`
(act: 1=left 2=right 3=middle) · `SCAL|ms` · `SETRES|w,h` · `HALT` / `BYE`

## TODO (next iterations)
1. Full If/Else modeling (Else branch is imported as a note comment today)
2. Get Point capture for Mouse Position (§5.5.2) + Cut BMP from screen (§5.5.11)
3. Run highlight on the current step + Debug Run (step-by-step, §2.4)
4. Native C# transport (option A) — removes the python.exe helper process
5. Hotkeys tab in Options (§5.5.8) + global Start/Stop hotkeys
6. Generated .ps1: Find Image / Play Script are TODO comments (run via the app instead)

## v0.6.2 (2026-08-21) — instant Stop

- **bridge.py v2**: ops run on a worker thread; new `abort` op writes HALT to the board out-of-band (write-only — the worker stays the sole reader) so a long WSND/TRGSND listen breaks immediately. Previously Stop queued behind the whole sound window and Run stayed disabled.
- Aborted commands emit `{"event":"aborted"}` (not `reply`) so reply-pairing is never disturbed.
- `IBoardBridge.SendAbortAsync` + Stop uses it; Run cleanup HALT now capped at 5s → the Run button always re-enables.
- AmkImporter: UTF-8 decoder pipes + concurrent stdout/stderr reads (adopted on-machine build fix).
- .amsj envelope version → 0.6.2.
