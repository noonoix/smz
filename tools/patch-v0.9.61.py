#!/usr/bin/env python3
"""Classroom Studio v0.9.61 - cursor sync before click/wheel + bridge link fixes.

Two layers, one repo patch:

1) RunEngine: before MCLICK/MWHEEL/MDOWN/MUP, sync the board to the REAL cursor
   position (Cursor.Position) with an instant abs MMOVE. Why: HID-Project's
   AbsoluteMouse resends its stored axes on every button/wheel report; those axes boot
   to (0,0) = screen centre, so a click/scroll without a prior board-driven move landed
   in the middle of the monitor (user report 2026-09-08). The board cannot read the
   cursor back - only the app knows it. (Arm fw 1.8 carries the same fix board-side.)

2) bridge.py (v0.9.60e), delegated to tools/patch_bridge_60e.py so the release patch
   and the repo patch never diverge:
   - PicoLink.command skips stale replies (a write-only abort HALT answer used to be
     paired with the next command: hardware log SETRES <- OK|HALT / OK|PONG).
   - the worker drains a dirty pipe before each send/send_path.
   - KTEXT gets a payload-sized timeout (len x hmax + margin).
   - a lone MMOVE sent as a "send" op is acked locally (firmware 60c made MMOVE
     fire-and-forget) - this is also what makes the 0.9.61 cursor sync free.

Version pins (csproj/curMinor/banner) are intentionally left to the release step:
apply, run the test suite, bump per convention, push.

Usage: python tools/patch-v0.9.61.py [repo-root]
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    # idempotency: the applied text is already there -> nothing to do
    if new in text:
        return text, False
    count = text.count(old)
    if count == 1:
        return text.replace(old, new, 1), True
    raise SystemExit(f"ERROR: {label}: expected one anchor, found {count}")


def patch_file(path: pathlib.Path, transforms) -> bool:
    if not path.exists():
        raise SystemExit(f"ERROR: missing {path}")
    original = path.read_text(encoding="utf-8")
    text = original
    changed_any = False
    for old, new, label in transforms:
        text, changed = replace_once(text, old, new, label)
        changed_any |= changed
    if changed_any:
        backup = path.with_suffix(path.suffix + ".bak-v0.9.61")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8", newline="")
        print(f"OK: patched {path}")
    else:
        print(f"already patched: {path}")
    return changed_any


RUNENGINE_OLD = (
    '                        else\n'
    '                        {\n'
    '                            await Send(wireCmd, ct,\n'
    '                                logAs: secret && cmd.StartsWith("KTEXT|") ? MaskKtext(cmd) : null);\n'
    '                        }\n'
)

RUNENGINE_NEW = (
    '                        else\n'
    '                        {\n'
    '                            // v0.9.61 — sync the board\'s tracked cursor to the REAL cursor before\n'
    '                            // button/wheel actions: HID-Project\'s AbsoluteMouse resends its stored\n'
    '                            // axes on every button/wheel report, and those axes boot to (0,0) =\n'
    '                            // screen centre, so a click/scroll without a prior board-driven move\n'
    '                            // landed in the middle of the monitor. The board cannot read the cursor\n'
    '                            // back; only the app knows it. Instant abs move = invisible (the cursor\n'
    '                            // is already there). Arm fw 1.8 carries the same fix board-side.\n'
    '                            if (cmd.StartsWith("MCLICK|") || cmd.StartsWith("MWHEEL|")\n'
    '                                || cmd.StartsWith("MDOWN|") || cmd.StartsWith("MUP|"))\n'
    '                            {\n'
    '                                var cur = System.Windows.Forms.Cursor.Position;\n'
    '                                await Send($"MMOVE|{cur.X},{cur.Y},abs,0", ct, quiet: true);\n'
    '                                _mouseAnchor = cur;\n'
    '                            }\n'
    '                            await Send(wireCmd, ct,\n'
    '                                logAs: secret && cmd.StartsWith("KTEXT|") ? MaskKtext(cmd) : null);\n'
    '                        }\n'
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Classroom Studio v0.9.61 - cursor sync + bridge link fixes")
    ap.add_argument("repo", nargs="?", default=".", help="repository root")
    args = ap.parse_args()
    root = pathlib.Path(args.repo).resolve()

    engine = root / "ams-shell/src/Ams.UI/Services/RunEngine.cs"
    patch_file(engine, [(RUNENGINE_OLD, RUNENGINE_NEW, "cursor sync before click/wheel")])

    # bridge side: same four fixes as the release patch - delegated so they never diverge
    bridge_patch = root / "tools/patch_bridge_60e.py"
    if not bridge_patch.exists():
        raise SystemExit("ERROR: tools/patch_bridge_60e.py missing - it ships in the same bundle/branch")
    rc = subprocess.run([sys.executable, str(bridge_patch),
                         str(root / "ams-shell/bridge/bridge.py")]).returncode
    if rc != 0:
        raise SystemExit("ERROR: bridge patch failed")

    print("v0.9.61 patch complete - run tests (cd tests && dotnet run -c Release), bump version pins, push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
