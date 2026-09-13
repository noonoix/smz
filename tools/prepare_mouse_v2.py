from pathlib import Path

p = Path("tools/apply_mouse_reliability_v2.py")
s = p.read_text(encoding="utf-8")
old = '''sub(exporter, r'public const string BundleVersion = "0\\.9\\.64f";', 'public const string BundleVersion = "0.9.64g";')\n'''
if s.count(old) != 1:
    raise SystemExit(f"expected one bundle-version edit, found {s.count(old)}")
p.write_text(s.replace(old, '# Keep BundleVersion 0.9.64f: AutoCycle compatibility contract.\n'), encoding="utf-8")
print("firmware compatibility version preserved")
