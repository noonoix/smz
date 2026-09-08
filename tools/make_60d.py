# make_60d.py - build code60d.py (production) from code60c.py.
# KTEXT ROOT CAUSE (hardware log): typeText -> ERR|EXC|KTEXT, nothing typed, but KCOMBO
# works. Proof from the board's own /lib bundle (adafruit_hid 6.1.10): keyboard.mpy has
# NO `write` method (strings show only press/release/release_all/_add_keycode_to_report).
# kbd.write(ch) raises AttributeError on the first char -> ERR|EXC -> the run dies.
# Fix = type via the PROVEN press/release primitives (same as KCOMBO) using an inline
# US-layout ASCII->keycode map, with a graceful getattr fallback (a missing name yields
# ERR|ASCII, never a crash). Per-key humanized delay kept (random.random, not uniform).
SRC = open("/data/code60c.py", encoding="utf-8").read()

edits = [
    # 1) insert the ASCII->keycode map + helper right after keycode_for_vk
    ("    return SPECIAL_VK.get(vk, MOD_VK.get(vk, Keycode.E))   # modifiers included\n"
     "\n\n"
     "class Bh1750:",
     "    return SPECIAL_VK.get(vk, MOD_VK.get(vk, Keycode.E))   # modifiers included\n"
     "\n\n"
     "# v0.9.60d - ASCII -> Keycode name for the US layout. The adafruit_hid 6.1.10 bundle on\n"
     "# /lib has NO Keyboard.write method, so KTEXT types via press/release instead.\n"
     "_KTEXT_PLAIN = {\n"
     "    \" \": \"SPACE\", \".\": \"PERIOD\", \",\": \"COMMA\", \"-\": \"MINUS\", \"=\": \"EQUALS\",\n"
     "    \"/\": \"FORWARD_SLASH\", \";\": \"SEMICOLON\", \"'\": \"QUOTE\", \"[\": \"LEFT_BRACKET\",\n"
     "    \"]\": \"RIGHT_BRACKET\", \"\\\\\": \"BACKSLASH\", \"`\": \"GRAVE_ACCENT\",\n"
     "}\n"
     "_KTEXT_SHIFTED = {\n"
     "    \"!\": \"ONE\", \"@\": \"TWO\", \"#\": \"THREE\", \"$\": \"FOUR\", \"%\": \"FIVE\", \"^\": \"SIX\",\n"
     "    \"&\": \"SEVEN\", \"*\": \"EIGHT\", \"(\": \"NINE\", \")\": \"ZERO\", \"_\": \"MINUS\",\n"
     "    \"+\": \"EQUALS\", \"?\": \"FORWARD_SLASH\", \":\": \"SEMICOLON\", \"\\\"\": \"QUOTE\",\n"
     "    \"{\": \"LEFT_BRACKET\", \"}\": \"RIGHT_BRACKET\", \"|\": \"BACKSLASH\", \"~\": \"GRAVE_ACCENT\",\n"
     "    \"<\": \"COMMA\", \">\": \"PERIOD\",\n"
     "}\n"
     "\n\n"
     "def _ascii_key(ch):\n"
     "    # returns (keycode, need_shift); (None, False) when the char is not US-printable\n"
     "    o = ord(ch)\n"
     "    if 97 <= o <= 122:                        # a-z\n"
     "        return getattr(Keycode, ch.upper(), None), False\n"
     "    if 65 <= o <= 90:                         # A-Z\n"
     "        return getattr(Keycode, ch, None), True\n"
     "    if 48 <= o <= 57:                         # 0-9 (reuse the proven DIGITS table)\n"
     "        return getattr(Keycode, DIGITS[o - 48], None), False\n"
     "    if ch in _KTEXT_PLAIN:\n"
     "        return getattr(Keycode, _KTEXT_PLAIN[ch], None), False\n"
     "    if ch in _KTEXT_SHIFTED:\n"
     "        return getattr(Keycode, _KTEXT_SHIFTED[ch], None), True\n"
     "    return None, False\n"
     "\n\n"
     "class Bh1750:"),
    # 2) rewrite the KTEXT branch: press/release instead of the missing kbd.write
    ("    if head == \"KTEXT\":\n"
     "        # KTEXT|hmin,hmax,text - ASCII only, per-key random delay\n"
     "        parts = line.split(\"|\", 1)[1].split(\",\", 2)\n"
     "        try:\n"
     "            hmin, hmax = int(parts[0]), int(parts[1])\n"
     "        except Exception:\n"
     "            hmin, hmax = 0, 0\n"
     "        txt = parts[2] if len(parts) > 2 else \"\"\n"
     "        for ch in txt:\n"
     "            if ord(ch) < 32 or ord(ch) > 126:\n"
     "                return \"ERR|ASCII|KTEXT\"\n"
     "        for ch in txt:\n"
     "            kbd.write(ch)\n"
     "            if hmax > 0:\n"
     "                time.sleep(random.uniform(max(0, hmin), hmax) / 1000)\n"
     "        return \"OK|KTEXT\"\n",
     "    if head == \"KTEXT\":\n"
     "        # KTEXT|hmin,hmax,text - v0.9.60d: type via press/release (kbd.write is absent on\n"
     "        # the adafruit_hid 6.1.10 bundle). Per-key humanized delay preserved.\n"
     "        parts = line.split(\"|\", 1)[1].split(\",\", 2)\n"
     "        try:\n"
     "            hmin, hmax = int(parts[0]), int(parts[1])\n"
     "        except Exception:\n"
     "            hmin, hmax = 0, 0\n"
     "        txt = parts[2] if len(parts) > 2 else \"\"\n"
     "        for ch in txt:\n"
     "            if _ascii_key(ch)[0] is None:\n"
     "                return \"ERR|ASCII|KTEXT\"\n"
     "        for ch in txt:\n"
     "            kc, sh = _ascii_key(ch)\n"
     "            if sh:\n"
     "                kbd.press(Keycode.LEFT_SHIFT)\n"
     "            kbd.press(kc)\n"
     "            kbd.release(kc)\n"
     "            if sh:\n"
     "                kbd.release(Keycode.LEFT_SHIFT)\n"
     "            if hmax > 0:\n"
     "                time.sleep((hmin + random.random() * (hmax - hmin if hmax > hmin else 0)) / 1000)\n"
     "        return \"OK|KTEXT\"\n"),
    # 3) visible version bump
    ("pico-light 0.9.60c|role=brain",
     "pico-light 0.9.60d|role=brain"),
]
for i, (a, b) in enumerate(edits):
    assert SRC.count(a) == 1, "anchor %d not unique (count=%d)" % (i, SRC.count(a))
    SRC = SRC.replace(a, b)

assert "kbd.write(" not in SRC, "kbd.write CALL still present"  # the explanatory comment may mention it
assert "pico-light 0.9.60d" in SRC
assert "def _ascii_key" in SRC
open("/data/code60d.py", "w", encoding="utf-8", newline="\n").write(SRC)
compile(SRC, "code60d.py", "exec")
print("compile OK")
print("make_60d: DONE")
