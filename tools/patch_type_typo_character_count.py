#!/usr/bin/env python3
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

replacements = [
    (
        "    words=0; i=0\n",
        "    chars_since_typo=0; i=0\n",
    ),
    (
        "        words+=1; due=typo_on and words>=next_typo and end-i>=2\n",
        "        due=typo_on and chars_since_typo>=next_typo and end-i>=2\n",
    ),
    (
        "                    words=0; next_typo=max(1,_type_roll(typo))\n",
        "                    owner.emit(\"EVT|DEBUG|STEP/TYPE typo-correction\")\n                    chars_since_typo=0; next_typo=max(1,_type_roll(typo))\n",
    ),
]
for old, new in replacements:
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("missing TYPE typo anchor: " + old.strip())

# The generated runtime has appeared with both compact and PEP-8 spacing over
# time (j+=1/i=end and j += 1/i = end). Match only the loop inside _light_type,
# so this patch is stable across both generator variants.
if "chars_since_typo += 1" not in s:
    start = s.find("def _light_type(")
    if start < 0:
        raise SystemExit("missing TYPE function anchor")
    end = s.find("\ndef ", start + 5)
    if end < 0:
        end = len(s)
    region = s[start:end]
    matches = list(re.finditer(r"(?m)^(?P<indent>[ \t]*)j\s*\+=\s*1\s*$", region))
    if len(matches) != 1:
        raise SystemExit("missing TYPE typo increment anchor: found " + str(len(matches)))
    m = matches[0]
    indent = m.group("indent")
    replacement = indent + "chars_since_typo += 1\n" + indent + "j += 1"
    region = region[:m.start()] + replacement + region[m.end():]
    s = s[:start] + region + s[end:]

if "chars_since_typo" not in s or "typo-correction" not in s:
    raise SystemExit("TYPE typo patch postcondition failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched character-based TYPE correction:", p)
