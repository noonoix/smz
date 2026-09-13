from pathlib import Path
p = Path('tests/TestRunner.cs')
s = p.read_text(encoding='utf-8')
old = 'the Insert menu lists all 24 step types, including Launch DC Recovery'
new = 'the Insert menu lists all 25 step types, including Launch DC Recovery'
if old not in s:
    raise SystemExit('stale step-count assertion not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
