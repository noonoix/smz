#!/usr/bin/env python3
from pathlib import Path
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
    (
        "            j+=1\n        i=end\n",
        "            chars_since_typo += 1\n            j+=1\n        i=end\n",
    ),
]
for old, new in replacements:
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit("missing TYPE typo anchor: " + old.strip())

if "chars_since_typo" not in s or "typo-correction" not in s:
    raise SystemExit("TYPE typo patch postcondition failed")
p.write_text(s, encoding="utf-8", newline="\n")
print("patched character-based TYPE correction:", p)
