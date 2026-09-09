#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resync PicoFirmwareExporter's CodeTemplate to golden code64b.

The source of truth is firmware/code64b/code64b.py. The C# raw string keeps the
seven live exporter placeholders while otherwise remaining byte-equivalent to
the golden firmware for its recorded generation values.

Safe to re-run: an already-patched exporter is only verified, not rewritten.
Usage: python tools/make_fw_template_0.9.64b.py [repo-root]
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

TARGET_VERSION = "0.9.64b"
VALUES = {
    "__MACHINE__": "sim",
    "__GENERATED__": "2026-09-09",
    "__VERSION__": TARGET_VERSION,
    "__STATE_COUNT__": "0",
    "__LOOP_MODE__": "once",
    "__LOOP_COUNT__": "0",
    "__LOOP_SECONDS__": "0",
}
PLACEHOLDERS = tuple(VALUES)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def extract_template(cs: str) -> str:
    marker = '    private const string CodeTemplate = """"\n'
    start = cs.index(marker) + len(marker)
    end = cs.index('\n        """";', start)
    out: list[str] = []
    for line in cs[start:end].split("\n"):
        if not line:
            out.append("")
        elif line.startswith("        "):
            out.append(line[8:])
        else:
            raise SystemExit(f"ERROR: lost raw-literal indent: {line[:70]!r}")
    return "\n".join(out)


def simulate(template: str) -> str:
    result = template
    for key, value in VALUES.items():
        result = result.replace(key, value)
    return result


def verify(cs: str, golden: str) -> None:
    template = extract_template(cs)
    counts = {key: template.count(key) for key in PLACEHOLDERS}
    expected = {
        "__MACHINE__": 1,
        "__GENERATED__": 1,
        "__VERSION__": 3,
        "__STATE_COUNT__": 1,
        "__LOOP_MODE__": 1,
        "__LOOP_COUNT__": 1,
        "__LOOP_SECONDS__": 1,
    }
    if counts != expected:
        raise SystemExit(f"ERROR: placeholder counts differ: {counts!r}")
    exported = simulate(template)
    if exported != golden:
        limit = min(len(exported), len(golden))
        pos = next((i for i in range(limit) if exported[i] != golden[i]), limit)
        print("FIRST DIFF @ char", pos)
        print("export:", repr(exported[max(0, pos - 60):pos + 60]))
        print("golden:", repr(golden[max(0, pos - 60):pos + 60]))
        print("lengths export/golden:", len(exported), len(golden))
        raise SystemExit("ERROR: template export differs from golden code64b.py")
    digest = hashlib.sha256(exported.encode("utf-8")).hexdigest()
    print("export simulation == golden code64b.py: BYTE-IDENTICAL")
    print("export sha256:", digest)
    print("placeholder counts:", counts)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    cs_path = root / "ams-shell/src/Ams.UI/Services/PicoFirmwareExporter.cs"
    gold_path = root / "firmware/code64b/code64b.py"
    cs = cs_path.read_text(encoding="utf-8")
    golden = gold_path.read_text(encoding="utf-8")

    already = (
        'public const string BundleVersion = "0.9.64b";' in cs
        and 'private const string CodeTemplate = """"' in cs
    )
    if already:
        verify(cs, golden)
        print("already patched: PicoFirmwareExporter.cs")
        return 0

    body = golden
    body = replace_once(
        body,
        "# Classroom Studio v0.9.64b - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)",
        "# Classroom Studio v__VERSION__ - Raspberry Pi Pico light-sensor + portable-plan firmware (CircuitPython)",
        "firmware title placeholder",
    )
    body = replace_once(
        body,
        "# System: sim   generated: 2026-09-09   calibrated states: 0",
        "# System: __MACHINE__   generated: __GENERATED__   calibrated states: __STATE_COUNT__",
        "generation metadata placeholders",
    )
    body = replace_once(body, 'LOOP_MODE = "once"', 'LOOP_MODE = "__LOOP_MODE__"', "loop mode placeholder")
    body = replace_once(body, "LOOP_COUNT = 0 ", "LOOP_COUNT = __LOOP_COUNT__ ", "loop count placeholder")
    body = replace_once(body, "LOOP_SECONDS = 0", "LOOP_SECONDS = __LOOP_SECONDS__", "loop seconds placeholder")
    body = replace_once(
        body,
        'return "OK|PONG|pico-light 0.9.64b|role=brain+keyboard+light|arm=promicro"',
        'return "OK|PONG|pico-light __VERSION__|role=brain+keyboard+light|arm=promicro"',
        "PONG version placeholder",
    )
    body = replace_once(
        body,
        'print("pico-light 0.9.64b | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause")',
        'print("pico-light __VERSION__ | GP4=NumLock start/stop (hold 1s=panic release) | GP3=ScrollLock pause")',
        "boot banner version placeholder",
    )

    if '""""' in body:
        raise SystemExit("ERROR: a four-quote run would break the C# raw literal")
    if '"""' not in body:
        raise SystemExit("ERROR: expected Python docstrings in golden firmware")
    whitespace_only = [i for i, line in enumerate(body.split("\n"), 1) if line and not line.strip()]
    if whitespace_only:
        raise SystemExit(f"ERROR: whitespace-only Python lines are unsafe for raw-indent trimming: {whitespace_only[:5]}")

    indented = "\n".join(("        " + line) if line else "" for line in body.split("\n"))
    open_anchor = '    private const string CodeTemplate = """'
    start = cs.index(open_anchor)
    end = cs.index('\n        """;', start) + len('\n        """;')
    cs = cs[:start] + '    private const string CodeTemplate = """"\n' + indented + '\n        """";' + cs[end:]

    cs = replace_once(
        cs,
        '    public const string BundleVersion = "0.9.60";   // v0.9.60 — hardened consolidation: optional sensor, byte buffer, arm pump, fixed keypad, Pico-only keyboard',
        '    public const string BundleVersion = "0.9.64b";   // v0.9.64b — template resynced to the golden standalone firmware line (code64b): plan engine + persistent cursor + ack watchdog + coalescing + conditional start/stop release + GP4 panic hold',
        "bundle version",
    )
    cs = replace_once(
        cs,
        "/// continuous H-resolution (0x10, ~120 ms/sample), lux = raw / 1.2.\n/// </summary>",
        "/// continuous H-resolution (0x10, ~120 ms/sample), lux = raw / 1.2.\n/// v0.9.64b - template body resynced to the golden standalone firmware (code64b): portable plan.txt\n/// engine + persistent cursor across Stop/Start, arm-ack watchdog, coalesced fire-and-forget MMOVE,\n/// press/release KTEXT typing, conditional start/stop button release + GP4 panic hold. plan_engine.py\n/// and plan.txt are NOT part of this bundle - the firmware boots bridge-only without them; the\n/// portable plan ships via its own zip (Classroom-Studio-code64b.zip).\n/// </summary>",
        "exporter summary",
    )
    cs = replace_once(
        cs,
        '        sb.AppendLine("- v0.9.60: mouse commands are fire-and-ack for smooth dense paths; arm events (EVT|) stream to the PC live");',
        '        sb.AppendLine("- v0.9.64b: dense mouse paths stream fire-and-forget with coalescing (the newest target always lands); clicks stay fire-and-ack; arm events (EVT|) stream to the PC live");\n        sb.AppendLine("- v0.9.64b: GP4 start/stop no longer teleports the cursor - the Pico tracks held buttons and releases only genuinely held ones (hold GP4 >= 1 s = panic release-all)");',
        "README protocol notes",
    )

    cs_path.write_text(cs, encoding="utf-8", newline="")
    verify(cs_path.read_text(encoding="utf-8"), golden)
    print("patched:", cs_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
