from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PRE_AUTO = ROOT / "firmware/autocycle-hostusb-v5/code.pre-autocycle.py"
AUTO = ROOT / "firmware/autocycle-hostusb-v5/code.py"
MANIFEST = ROOT / "portable/plan3/autocycle_h6_patch.json"
TARGETS = (
    ROOT / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs",
    ROOT / "firmware/pico-light-0.9.60-template.py",
    ROOT / "firmware/code64f/code.py",
    PRE_AUTO,
)
SEQ_LINE = "_lux_seq = 0       # read-only LUX? sequence; resets on every Pico boot\n"


def replace_once(text, old, new, label):
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch(path):
    text = path.read_text(encoding="utf-8")
    original = text
    embedded = path.suffix.lower() == ".cs"
    p = "        " if embedded else ""

    window = p + "window = []\n"
    seq = window + p + SEQ_LINE
    text = replace_once(text, window, seq, f"{path}: sequence")

    sample_anchor = p + "def sample():\n"
    helper = (
        p + "def read_lux_telemetry():\n"
        + p + "    # Read-only telemetry: no key, mouse, buzzer, calibration or plan side effect.\n"
        + p + "    global _lux_seq\n"
        + p + "    if sensor is None:\n"
        + p + "        return \"ERR|NOSENSOR|LUX\"\n"
        + p + "    if _arm_lag > 0 or _pending_move is not None:\n"
        + p + "        return \"ERR|BUSY|LUX\"\n"
        + p + "    try:\n"
        + p + "        value = sensor.lux()\n"
        + p + "    except Exception:\n"
        + p + "        return \"ERR|I2C|LUX\"\n"
        + p + "    if value is None or value != value or value < 0:\n"
        + p + "        return \"ERR|I2C|LUX\"\n"
        + p + "    _lux_seq = (_lux_seq + 1) & 0xFFFFFFFF\n"
        + p + "    mode = \"lowres\" if sensor.mode == CONT_LORES else \"hires\"\n"
        + p + "    return \"OK|LUX|seq=%d|lux=%.1f|mode=%s|sensor=ok\" % (_lux_seq, value, mode)\n"
        + p + "\n"
        + p + "\n"
    )
    text = replace_once(text, sample_anchor, helper + sample_anchor, f"{path}: helper")

    ping = p + "    if line == \"PING\":\n"
    dispatch = p + "    if line == \"LUX?\":\n" + p + "        return read_lux_telemetry()\n"
    text = replace_once(text, ping, dispatch + ping, f"{path}: dispatch")

    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
        print("patched", path.relative_to(ROOT))
    else:
        print("already patched", path.relative_to(ROOT))


def load_telemetry_manifest():
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if document.get("version") != 1 or not document.get("edits"):
        raise RuntimeError("invalid AutoCycle manifest")
    changed = False
    anchor = "states = load_states()\nwindow = []\n"
    anchor_with_seq = anchor + SEQ_LINE
    for edit in document["edits"]:
        if anchor in edit["old"] or anchor_with_seq in edit["old"]:
            if anchor_with_seq not in edit["old"]:
                edit["old"] = edit["old"].replace(anchor, anchor_with_seq, 1)
                changed = True
            if anchor_with_seq not in edit["new"]:
                edit["new"] = edit["new"].replace(anchor, anchor_with_seq, 1)
                changed = True
            break
    else:
        raise RuntimeError("AutoCycle state/window manifest edit missing")
    if changed:
        MANIFEST.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print("updated", MANIFEST.relative_to(ROOT))
    return document


def sync_auto_cycle(document):
    actual = PRE_AUTO.read_text(encoding="utf-8")
    if document.get("baseline") not in actual:
        raise RuntimeError("AutoCycle baseline marker missing")
    for index, edit in enumerate(document["edits"], 1):
        count = actual.count(edit["old"])
        if count != 1:
            raise RuntimeError(f"AutoCycle anchor {index}: expected one, found {count}")
        actual = actual.replace(edit["old"], edit["new"], 1)
    if AUTO.read_text(encoding="utf-8") != actual:
        AUTO.write_text(actual, encoding="utf-8", newline="\n")
        print("synchronized", AUTO.relative_to(ROOT))
    else:
        print("already synchronized", AUTO.relative_to(ROOT))


for target in TARGETS:
    if not target.exists():
        raise RuntimeError(f"missing target: {target}")
    patch(target)
sync_auto_cycle(load_telemetry_manifest())
