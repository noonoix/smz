from pathlib import Path

p = Path("tools/sync_autocycle_mouse.py")
s = p.read_text(encoding="utf-8")
blocks = [
r'''        code=RequireReplace(code,
            "                return self._ok(forward_to_arm(line, _mclick_timeout(line)), \"MCLICK\")\n\n            def ktext",
            "                forward_fast(line)\n\n            def ktext","normal plan MCLICK dispatch");
''',
r'''        code=RequireReplace(code,
            "                forward_fast(line)\n\n            def ktext",
            "                return self._ok(forward_to_arm(line, _mclick_timeout(line)), \"MCLICK\")\n\n            def ktext","cycle plan MCLICK dispatch");
''']
for block in blocks:
    count = s.count(block)
    if count != 1:
        raise SystemExit(f"expected one plan-context block, found {count}")
    s = s.replace(block, "")
p.write_text(s, encoding="utf-8")
print("AutoCycle keeps the already-reliable plan MCLICK implementation")
