#!/usr/bin/env python3
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
helper=r'''def _type_pair(value, default_lo=0, default_hi=0):
    if value is None: return default_lo, default_hi
    a=value.split(",")
    if len(a)!=2: raise ValueError("bad TYPE range")
    lo=int(a[0]); hi=int(a[1])
    if lo<0 or hi<0: raise ValueError("negative TYPE range")
    if hi<lo: lo,hi=hi,lo
    return lo,hi


def _type_roll(pair):
    return pair[0] if pair[1]<=pair[0] else _light_random.randint(pair[0],pair[1])


def _type_decode(value):
    out=[]; i=0
    while i<len(value):
        if value[i]=="%" and i+2<len(value):
            try:
                out.append(chr(int(value[i+1:i+3],16))); i+=3; continue
            except Exception: pass
        out.append(value[i]); i+=1
    return "".join(out)


def _type_key(ch):
    o=ord(ch)
    if 97<=o<=122: return o-93,False
    if 65<=o<=90: return o-61,True
    if 49<=o<=57: return o-19,False
    if ch=="0": return 39,False
    if ch==" ": return 44,False
    if ch=="\t": return 43,False
    if ch in "\r\n": return 40,False
    plain="-=[]\\;'`,./"
    shifted="_+{}|:\"~<>?"
    i=plain.find(ch)
    if i>=0:
        return (45,46,47,48,49,51,52,53,54,55,56)[i],False
    i=shifted.find(ch)
    if i>=0:
        return (45,46,47,48,49,51,52,53,54,55,56)[i],True
    symbols="!@#$%^&*()"
    i=symbols.find(ch)
    if i>=0: return (30,31,32,33,34,35,36,37,38,39)[i],True
    raise ValueError("TYPE supports exported ASCII text only")


def _type_char(owner,ch,hold,expected):
    code,shift=_type_key(ch); down=0
    try:
        if shift: owner.keyboard.press(225); down=1
        owner.keyboard.press(code); down=2
        if not _light_sleep(owner,_type_roll(hold),expected): return False
        owner.keyboard.release(code); down=1 if shift else 0
        if shift: owner.keyboard.release(225); down=0
        return _light_gate(owner,expected)
    finally:
        if down>=2:
            try: owner.keyboard.release(code)
            except Exception: pass
        if down>=1 and shift:
            try: owner.keyboard.release(225)
            except Exception: pass


def _type_neighbor(ch):
    low=ch.lower()
    for row in ("1234567890","qwertyuiop","asdfghjkl","zxcvbnm"):
        i=row.find(low)
        if i>=0:
            j=i+(-1 if _light_random.randrange(2)==0 else 1)
            if j<0 or j>=len(row): j=1 if i==0 else i-1
            n=row[j]
            return n.upper() if ch.isupper() else n
    return None


def _light_type(owner,args,expected):
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
    words=0; i=0
    owner.emit("EVT|DEBUG|STEP/TYPE chars=%d" % len(text))
    while i<len(text):
        if text[i].isspace():
            if not _type_char(owner,text[i],hold,expected): return False
            i+=1; continue
        end=i
        while end<len(text) and not text[end].isspace(): end+=1
        words+=1; due=typo_on and words>=next_typo and end-i>=2
        typo_pos=i+1+_light_random.randrange(end-i-1) if due else -1
        j=i
        while j<end:
            if j==typo_pos:
                wrong=_type_neighbor(text[j])
                if wrong is not None:
                    if not _type_char(owner,wrong,hold,expected): return False
                    if not _light_sleep(owner,_light_random.randint(max(hold[1],120),hold[1]*2+200),expected): return False
                    if not _type_char(owner,"\b" if False else chr(8),hold,expected): return False
                    if not _light_sleep(owner,_type_roll(hold),expected): return False
                    words=0; next_typo=max(1,_type_roll(typo))
            if not _type_char(owner,text[j],hold,expected): return False
            if text[j] in ".,!?;:" and punct[1]>0:
                if not _light_sleep(owner,_type_roll(punct),expected): return False
            j+=1
        if end<len(text):
            if word[1]>0 and _light_random.randrange(100)<wp:
                if not _light_sleep(owner,_type_roll(word),expected): return False
            if think_chance>0 and think[1]>0 and _light_random.randrange(100)<think_chance:
                if not _light_sleep(owner,_type_roll(think),expected): return False
        i=end
    return True

'''
# Backspace is control char and needs an explicit mapping.
helper=helper.replace('    if ch=="\\t": return 43,False\n', '    if ch=="\\t": return 43,False\n    if ord(ch)==8: return 42,False\n')
anchor='def _run_light_route(owner, name):\n'
if helper not in s and "def _light_type(" not in s:
    if anchor not in s: raise SystemExit('missing TYPE helper anchor')
    s=s.replace(anchor,helper+anchor,1)
s=s.replace('{"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "KEY", "KDOWN", "KUP"}', '{"PLAN", "SCREEN", "SPEED", "BEEP", "DELAY", "LOOP", "LOOPTIME", "ENDLOOP", "KEY", "KDOWN", "KUP", "TYPE"}',1)
old='''            elif op == "KEY":
                if not _light_key(owner, args, expected): return
            elif op in ("KDOWN", "KUP"):'''
new='''            elif op == "KEY":
                if not _light_key(owner, args, expected): return
            elif op == "TYPE":
                if not _light_type(owner, args, expected): return
            elif op in ("KDOWN", "KUP"):'''
if old in s: s=s.replace(old,new,1)
elif new not in s and 'elif op == "TYPE":' not in s: raise SystemExit('missing TYPE dispatch anchor')
p.write_text(s,encoding='utf-8',newline='\n'); print('patched streaming TYPE:',p)
