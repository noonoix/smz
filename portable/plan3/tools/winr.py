#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""winr.py - compile "run a program / open a file / play a sound" steps into a
portable plan macro that needs NO PC-side helper: Win+R, the command, Enter.

Why this exists
---------------
runExe / openFile / playAudio are the only Classroom Studio steps that ask the PC to
start something. A keyboard is all the Pico has, so the portable equivalent is the
Run box. This module writes that macro for us, with three visibility modes:

  mode=visible : the plain path. The Run box flashes, the app opens normally.
  mode=min     : cmd /c start /min ""  -> the app starts minimised (short console flash).
  mode=hidden  : powershell -w hidden -c "Start-Process -WindowStyle Hidden ..."
                 -> no PowerShell window at all. Console apps and well-behaved apps
                    stay invisible; a GUI app that ignores WindowStyle still shows its
                    own window (nothing typed on a keyboard can prevent that).

Honest limits (documented, never silently ignored):
  * The Run box itself is always visible for a moment: ~200-400 ms, small, bottom-left.
  * Win+R writes the typed line into the RunMRU history. clean_mru=True appends a
    Remove-ItemProperty that wipes that history in the same hidden command.
  * KTEXT is ASCII only, so a path with Persian/Unicode characters cannot be typed.
    Use pinned(index) (Win+1..9 on a taskbar icon), an 8.3 short path, or copy the
    target to an ASCII path.

Everything here returns plain plan lines, so plan_check.py / the engine validate them.
"""
import argparse
import sys

VK_LWIN = 91
VK_R = 82
VK_ENTER = 13
VK_DIGIT = {1: 49, 2: 50, 3: 51, 4: 52, 5: 53, 6: 54, 7: 55, 8: 56, 9: 57}

MRU_CLEAN = ("; Remove-ItemProperty "
             "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU' "
             "-Name * -EA 0")


def pct(text):
    """Percent-encode what the plan format cannot carry literally ('|' and '%').
    Non-ASCII is a hard error: the board types ASCII only."""
    out = []
    for ch in text:
        code = ord(ch)
        if code > 126 or code < 32:
            raise ValueError(
                "non-ASCII/control character %r in '%s' - the board cannot type it. "
                "Use a pinned taskbar icon (Win+1..9), an 8.3 short path, or an ASCII path."
                % (ch, text))
        if ch in "|%":
            out.append("%%%02X" % code)
        else:
            out.append(ch)
    return "".join(out)


def _q(path):
    return '"%s"' % path if " " in path else path


def _ps(path):
    return path.replace("'", "''")


def run_command(path, args="", mode="hidden", clean_mru=True, shell_open=False):
    """Return the exact text that gets typed into the Run box."""
    if mode == "visible":
        return (_q(path) + ((" " + args) if args else ""))
    if mode == "min":
        return 'cmd /c start /min "" %s%s' % (_q(path), (" " + args) if args else "")
    if mode != "hidden":
        raise ValueError("unknown mode '%s' (visible|min|hidden)" % mode)
    inner = "Start-Process "
    if not shell_open:
        inner += "-WindowStyle Hidden "
    inner += "-FilePath '%s'" % _ps(path)
    if args:
        inner += " -ArgumentList '%s'" % _ps(args)
    if clean_mru:
        inner += MRU_CLEAN
    return 'powershell -w hidden -c "%s"' % inner


def audio_command(path, seconds=0, clean_mru=True):
    """Background audio with no window at all (playAudio mode=playerMacro)."""
    low = path.lower()
    if low.endswith(".wav"):
        inner = "(New-Object Media.SoundPlayer '%s').PlaySync()" % _ps(path)
    else:
        inner = ("Add-Type -AssemblyName presentationCore;"
                 "$p=New-Object System.Windows.Media.MediaPlayer;"
                 "$p.Open([uri]'%s');$p.Play()" % _ps(path))
        if seconds > 0:
            inner += ";Start-Sleep -Seconds %d" % int(seconds)
    if clean_mru:
        inner += MRU_CLEAN
    return 'powershell -w hidden -c "%s"' % inner


def macro(command, label, settle=(600, 1200), open_wait=(350, 650),
          confirm_wait=(140, 260), gate=None):
    """Win+R -> type command -> Enter, as plan lines. `gate` is an optional
    WLIGHT spec ('lo,hi,stable,to,mode') used as a before/after screen-light gate."""
    lines = ["# %s" % label]
    if gate:
        lines.append("WLIGHT|%s" % gate)
    lines += [
        "KEY|combo=%d+%d|hold=40,90" % (VK_LWIN, VK_R),
        "DELAY|%d,%d" % open_wait,
        "TYPE|text=%s" % pct(command),
        "DELAY|%d,%d" % confirm_wait,
        "KEY|combo=%d|hold=40,90" % VK_ENTER,
        "DELAY|%d,%d" % settle,
    ]
    if gate:
        lines.append("WLIGHT|%s" % gate)
    return lines


def launch(path, args="", mode="hidden", clean_mru=True, shell_open=False, gate=None,
           settle=(600, 1200)):
    """runExe (shell_open=False) / openFile (shell_open=True) as plan lines."""
    cmd = run_command(path, args, mode, clean_mru, shell_open)
    kind = "openFile" if shell_open else "runExe"
    return macro(cmd, "%s mode=%s: %s" % (kind, mode, path), settle=settle, gate=gate)


def audio(path, seconds=0, clean_mru=True, gate=None):
    """playAudio mode=playerMacro (background, no window) as plan lines."""
    return macro(audio_command(path, seconds, clean_mru),
                 "playAudio playerMacro (background): %s" % path,
                 settle=(200, 400), gate=gate)


def pinned(index, settle=(600, 1200)):
    """Zero-footprint launcher: Win+1..9 on a pinned taskbar icon. No Run box, no MRU."""
    if index not in VK_DIGIT:
        raise ValueError("pinned index must be 1..9")
    return [
        "# runExe mode=pinned: Win+%d (taskbar icon %d)" % (index, index),
        "KEY|combo=%d+%d|hold=40,90" % (VK_LWIN, VK_DIGIT[index]),
        "DELAY|%d,%d" % settle,
    ]


def main():
    ap = argparse.ArgumentParser(description="compile launcher steps into plan lines")
    ap.add_argument("kind", choices=("exe", "open", "audio", "pinned"))
    ap.add_argument("--path", default="")
    ap.add_argument("--args", default="")
    ap.add_argument("--mode", default="hidden", choices=("visible", "min", "hidden"))
    ap.add_argument("--seconds", type=int, default=0)
    ap.add_argument("--index", type=int, default=1)
    ap.add_argument("--keep-mru", action="store_true")
    ap.add_argument("--gate", default=None, help="WLIGHT spec: lo,hi,stable,to,mode")
    a = ap.parse_args()
    clean = not a.keep_mru
    if a.kind == "pinned":
        out = pinned(a.index)
    elif a.kind == "audio":
        out = audio(a.path, a.seconds, clean, a.gate)
    else:
        out = launch(a.path, a.args, a.mode, clean, a.kind == "open", a.gate)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
