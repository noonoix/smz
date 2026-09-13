from pathlib import Path
p = Path('tests/TestRunner.cs')
s = p.read_text(encoding='utf-8')
old = 'Assert(v43insert.Count == 24,'
new = 'Assert(v43insert.Count == 25,'
if old not in s:
    raise SystemExit('stale count assertion not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
