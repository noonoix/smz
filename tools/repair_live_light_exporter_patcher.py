from pathlib import Path

# The correction is deliberately idempotent so the CI repair remains safe on retries.
p = Path(__file__).with_name('apply_live_light_exporter.py')
text = p.read_text(encoding='utf-8')
old = 'if "EmitLiveLightStateLoop" not in tpl:'
new = 'if method_marker not in tpl:'
if old in text:
    p.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')
    print('repaired exporter patcher')
else:
    print('exporter patcher already repaired')
