#!/usr/bin/env python3
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

# Replace the whole TYPE loop instead of changing a word counter in place. The
# old implementation decided `due` once per word, so a typo configured every
# N characters was silently delayed to a later word and often never appeared
# in short strings. This version checks the counter before every character.
start = re.search(r"(?m)^def _light_type\(owner,\s*args,\s*expected\):\s*$", s)
if not start:
    raise SystemExit("missing TYPE function anchor")
end = re.search(r"(?m)^def _mouse_pair\(", s[start.end():])
if not end:
    raise SystemExit("missing TYPE function end anchor")
end_pos = start.end() + end.start()

new_type = '''def _light_type(owner,args,expected):
    vals={}
    for field in args.split("|"):
        if "=" not in field: raise ValueError("bad TYPE field")
        k,v=field.split("=",1); vals[k]=v
    if "text" not in vals: raise ValueError("TYPE needs text")
    text=_type_decode(vals["text"])
    hold=_type_pair(vals.get("h"),80,220)
    word=_type_pair(vals.get("w"),0,0)
    punct=_type_pair(vals.get("p"),0,0)
    typo=_type_pair(vals.get("typo"),0,0)
    wp=max(0,min(100,int(vals.get("wp","100"))))
    think_chance=0; think=(800,2200)
    if "think" in vals:
        a=vals["think"].split(":",1)
        if len(a)!=2: raise ValueError("bad TYPE think")
        think_chance=max(0,min(100,int(a[0]))); think=_type_pair(a[1])
    typo_on=typo[1]>0
    next_typo=max(1,_type_roll(typo)) if typo_on else -1
    chars_since_typo=0; i=0
    owner.emit("EVT|DEBUG|STEP/TYPE chars=%d typo=%s" % (len(text), "on" if typo_on else "off"))
    while i<len(text):
        ch=text[i]
        if typo_on and not ch.isspace() and chars_since_typo>=next_typo:
            wrong=_type_neighbor(ch)
            if wrong is not None:
                if not _type_char(owner,wrong,hold,expected): return False
                if not _light_sleep(owner,_light_random.randint(max(hold[1],120),hold[1]*2+200),expected): return False
                if not _type_char(owner,chr(8),hold,expected): return False
                if not _light_sleep(owner,_type_roll(hold),expected): return False
                owner.emit("EVT|DEBUG|STEP/TYPE typo-correction char=%d" % i)
                chars_since_typo=0
                next_typo=max(1,_type_roll(typo))
        if not _type_char(owner,ch,hold,expected): return False
        chars_since_typo += 1
        if ch in ".,!?;:" and punct[1]>0:
            if not _light_sleep(owner,_type_roll(punct),expected): return False
        if ch.isspace():
            if word[1]>0 and _light_random.randrange(100)<wp:
                if not _light_sleep(owner,_type_roll(word),expected): return False
            if think_chance>0 and think[1]>0 and _light_random.randrange(100)<think_chance:
                if not _light_sleep(owner,_type_roll(think),expected): return False
        i+=1
    return True

'''
s = s[:start.start()] + new_type + s[end_pos:]

# Extend neighbouring-key selection to digits as well; otherwise a random
# typo landing on a number was skipped with no correction at all.
neighbor = re.search(r"(?ms)^def _type_neighbor\(ch\):\n.*?^\ndef _light_type\(", s)
if not neighbor:
    raise SystemExit("missing neighbor helper anchor")
new_neighbor = '''def _type_neighbor(ch):
    low=ch.lower()
    for row in ("1234567890","qwertyuiop","asdfghjkl","zxcvbnm"):
        i=row.find(low)
        if i>=0:
            j=i+(-1 if _light_random.randrange(2)==0 else 1)
            if j<0 or j>=len(row): j=1 if i==0 else i-1
            n=row[j]
            return n.upper() if ch.isupper() else n
    return None


def _light_type('''
s = s[:neighbor.start()] + new_neighbor + s[neighbor.end()-len("def _light_type("):]

if "chars_since_typo>=next_typo" not in s or "typo-correction" not in s:
    raise SystemExit("TYPE character-based correction postcondition failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched character-based TYPE correction:", p)
