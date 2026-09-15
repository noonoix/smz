from pathlib import Path
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
TEMPLATE = ROOT / "firmware/pico-light-0.9.60-template.py"
GOLDEN = ROOT / "firmware/code64f/code.py"
PRE_AUTO = ROOT / "firmware/autocycle-hostusb-v5/code.pre-autocycle.py"
AUTO = ROOT / "firmware/autocycle-hostusb-v5/code.py"
MANIFEST = ROOT / "portable/plan3/autocycle_h6_patch.json"
TARGETS = (EXPORTER, TEMPLATE, GOLDEN, PRE_AUTO, AUTO)

REQUIRED = (
    'if line == "LUX?":',
    'ERR|NOSENSOR|LUX',
    'ERR|I2C|LUX',
    'ERR|BUSY|LUX',
    'OK|LUX|seq=%d|lux=%.1f|mode=%s|sensor=ok',
    'if line.startswith("LCAL|"):',
    'if line.startswith("WLUX|"):',
    'if line.startswith("TRGLUX|"):',
)

for path in TARGETS:
    text = path.read_text(encoding="utf-8")
    for marker in REQUIRED:
        assert marker in text, f"{path}: missing {marker}"
    assert text.count('if line == "LUX?":') == 1, f"{path}: duplicate LUX? dispatch"

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
actual = PRE_AUTO.read_text(encoding="utf-8")
for index, edit in enumerate(manifest["edits"], 1):
    assert actual.count(edit["old"]) == 1, f"AutoCycle anchor {index} is not unique"
    actual = actual.replace(edit["old"], edit["new"], 1)
assert actual == AUTO.read_text(encoding="utf-8"), "AutoCycle firmware lost byte parity"

source = GOLDEN.read_text(encoding="utf-8")
match = re.search(r"^def read_lux_telemetry\(\):\n(.*?)(?=^def sample\(\):)", source, re.M | re.S)
assert match, "telemetry helper not found"
namespace = {"_lux_seq": 0, "_arm_lag": 0, "_pending_move": None, "CONT_LORES": 0x13}
exec("def read_lux_telemetry():\n" + textwrap.indent(textwrap.dedent(match.group(1)), "    "), namespace)
read = namespace["read_lux_telemetry"]

namespace["sensor"] = None
assert read() == "ERR|NOSENSOR|LUX"
assert namespace["_lux_seq"] == 0

class Sensor:
    mode = 0x10
    def lux(self): return 1284.7

namespace["sensor"] = Sensor()
namespace["_arm_lag"] = 1
assert read() == "ERR|BUSY|LUX"
assert namespace["_lux_seq"] == 0
namespace["_arm_lag"] = 0
namespace["_pending_move"] = "MMOVE|10,20,abs,2"
assert read() == "ERR|BUSY|LUX"
assert namespace["_lux_seq"] == 0
namespace["_pending_move"] = None
assert read() == "OK|LUX|seq=1|lux=1284.7|mode=hires|sensor=ok"
assert read().startswith("OK|LUX|seq=2|")
namespace["sensor"].mode = 0x13
assert "|mode=lowres|" in read()

class BrokenSensor:
    mode = 0x10
    def lux(self): raise OSError("i2c")

seq_before_error = namespace["_lux_seq"]
namespace["sensor"] = BrokenSensor()
assert read() == "ERR|I2C|LUX"
assert namespace["_lux_seq"] == seq_before_error

class InvalidSensor:
    mode = 0x10
    def lux(self): return float("nan")

namespace["sensor"] = InvalidSensor()
assert read() == "ERR|I2C|LUX"
assert namespace["_lux_seq"] == seq_before_error
print("light telemetry protocol: all contract tests passed")
