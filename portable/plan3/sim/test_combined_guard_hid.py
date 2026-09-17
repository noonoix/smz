# Internal HID and low-memory key-mapping fail-closed contract.
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "firmware" / "pico-light-guard-1.0.0" / "combined_guard_runtime.py"
source = RUNTIME.read_text(encoding="utf-8")
assert "from adafruit_hid" not in source
assert "class Keycode:" not in source

tree = ast.parse(source)
keyboard_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Keyboard")
combined_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Combined")
key_node = next(node for node in combined_node.body if isinstance(node, ast.FunctionDef) and node.name == "key")
key_only_combined = ast.ClassDef(
    name="Combined", bases=[], keywords=[], body=[key_node], decorator_list=[]
)
module = ast.fix_missing_locations(ast.Module(body=[keyboard_node, key_only_combined], type_ignores=[]))
namespace = {}
exec(compile(module, str(RUNTIME), "exec"), namespace)
Keyboard = namespace["Keyboard"]
Combined = namespace["Combined"]

key = Combined().key
for vk, usage in {
    65: 4, 90: 29, 49: 30, 57: 38, 48: 39,
    112: 58, 123: 69, 13: 40, 27: 41, 8: 42, 9: 43, 32: 44,
    37: 80, 38: 82, 39: 79, 40: 81,
    160: 225, 162: 224, 164: 226, 91: 227,
    0: 8,
}.items():
    assert key(vk) == usage, (vk, key(vk), usage)

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
keyboard.press(225, 4)
assert device.reports[-1] == bytes((0x02, 0, 4, 0, 0, 0, 0, 0))
keyboard.release(4)
assert device.reports[-1] == bytes((0x02, 0, 0, 0, 0, 0, 0, 0))
keyboard.release_all()
assert device.reports[-1] == bytes(8)

keyboard.press(4, 5, 6, 7, 8, 9)
try:
    keyboard.press(10)
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
print("PASS: combined Guard low-memory internal HID keyboard")
