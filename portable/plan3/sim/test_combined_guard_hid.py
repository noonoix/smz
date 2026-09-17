import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "firmware" / "pico-light-guard-1.0.0" / "combined_guard_runtime.py"
source = RUNTIME.read_text(encoding="utf-8")
assert "from adafruit_hid" not in source

tree = ast.parse(source)
selected = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in {"Keycode", "Keyboard"}]
assert {node.name for node in selected} == {"Keycode", "Keyboard"}
module = ast.Module(body=selected, type_ignores=[])
namespace = {}
exec(compile(module, str(RUNTIME), "exec"), namespace)
Keycode = namespace["Keycode"]
Keyboard = namespace["Keyboard"]

class Device:
    usage_page = 0x01
    usage = 0x06
    def __init__(self): self.reports = []
    def send_report(self, report): self.reports.append(bytes(report))

class OtherDevice:
    usage_page = 0x0C
    usage = 0x01

device = Device()
keyboard = Keyboard((OtherDevice(), device))
keyboard.press(Keycode.LEFT_SHIFT, Keycode.A)
assert device.reports[-1] == bytes((0x02, 0, 4, 0, 0, 0, 0, 0))
keyboard.release(Keycode.A)
assert device.reports[-1] == bytes((0x02, 0, 0, 0, 0, 0, 0, 0))
keyboard.release_all()
assert device.reports[-1] == bytes(8)

keyboard.press(Keycode.A, Keycode.B, Keycode.C, Keycode.D, Keycode.E, Keycode.F)
try:
    keyboard.press(Keycode.G)
except ValueError:
    pass
else:
    raise AssertionError("six-key rollover must reject a seventh key")
keyboard.release_all()

try:
    Keyboard((OtherDevice(),))
except RuntimeError:
    pass
else:
    raise AssertionError("missing keyboard device must fail closed")

assert "self.keyboard.release_all()" in source
print("PASS: combined Guard internal HID keyboard")
