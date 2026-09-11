# Generated from canonical plan_engine.py; do not hand-edit.
import time
import math
import random

def _below(n):
    return random.randrange(n) if n > 0 else 0

def rand_range(mn, mx):
    if mx < mn:
        mn, mx = (mx, mn)
    if mx <= 0:
        return 0
    return mn if mx <= mn else random.randint(mn, mx)

def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v
_QWERTY_ROWS = ('1234567890', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm')
_PUNCT = '.,!?;:'

def _qwerty_neighbor(ch):
    lower = ch.lower()
    for row in _QWERTY_ROWS:
        i = row.find(lower)
        if i < 0:
            continue
        j = i + (-1 if _below(2) == 0 else 1)
        if j < 0 or j >= len(row):
            j = 1 if i == 0 else i - 1
        n = row[j]
        return n.upper() if ch.isupper() else n
    return None

def _split_punct(s):
    outp = []
    start = 0
    for i in range(len(s) - 1):
        if s[i] in _PUNCT:
            outp.append(s[start:i + 1])
            start = i + 1
    if start < len(s):
        outp.append(s[start:])
    if not outp and s:
        outp.append(s)
    return outp

def plan_typing(text, p):
    hmin, hmax = p.get('h', (80, 220))
    wmin, wmax = p.get('w', (0, 0))
    wp = _clamp(p.get('wp', 100), 0, 100)
    pmin, pmax = p.get('p', (0, 0))
    think_chance, think_range = p.get('think', (0, (800, 2200)))
    think_chance = _clamp(think_chance, 0, 100)
    think_min, think_max = think_range
    typo_min, typo_max = p.get('typo', (0, 0))
    typo_cadence = typo_max > 0
    next_typo_at = max(1, rand_range(typo_min, typo_max)) if typo_cadence else -1
    words_since_typo = 0
    word_mode = wmax > 0 or pmax > 0 or think_chance > 0 or typo_cadence
    cmds = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    pending = []

    def flush():
        s = ''.join(pending)
        pending.clear()
        for i in range(0, len(s), 60):
            cmds.append(('KTEXT', hmin, hmax, s[i:i + 60]))
    for li, line in enumerate(lines):
        if word_mode:
            words = [wd for wd in line.split() if wd]
            for wi, word in enumerate(words):
                tail = ' ' if wi < len(words) - 1 else ''
                typed = word + tail
                typo_due = typo_cadence and (words_since_typo := (words_since_typo + 1)) >= next_typo_at
                if typo_due and 2 <= len(word) <= 60:
                    pos = 1 + _below(len(word) - 1)
                    wrong = _qwerty_neighbor(word[pos])
                    if wrong is not None:
                        flush()
                        cmds.append(('KTEXT', hmin, hmax, word[:pos] + wrong))
                        cmds.append(('DLY', rand_range(max(hmax, 120), hmax * 2 + 200)))
                        cmds.append(('KCOMBO', 8))
                        cmds.append(('DLY', rand_range(hmin, hmax)))
                        typed = word[pos:] + tail
                        words_since_typo = 0
                        next_typo_at = max(1, rand_range(typo_min, typo_max))
                segs = _split_punct(typed) if pmax > 0 else [typed]
                for si, seg in enumerate(segs):
                    pending.append(seg)
                    if si < len(segs) - 1:
                        flush()
                        cmds.append(('DLY', rand_range(pmin, pmax)))
                if wi < len(words) - 1:
                    if wmax > 0 and _below(100) < wp:
                        flush()
                        cmds.append(('DLY', rand_range(wmin, wmax)))
                    if think_chance > 0 and think_max > 0 and (_below(100) < think_chance):
                        flush()
                        cmds.append(('DLY', rand_range(think_min, think_max)))
            flush()
        else:
            for i in range(0, len(line), 60):
                cmds.append(('KTEXT', hmin, hmax, line[i:i + 60]))
        if li < len(lines) - 1:
            cmds.append(('KCOMBO', 13))
    return cmds
