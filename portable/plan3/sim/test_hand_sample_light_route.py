#!/usr/bin/env python3
"""The 10-second hand path must not import/parse the large PLAN engine on RP2040."""
import ast
from pathlib import Path
from types import SimpleNamespace

code_path = Path(__file__).resolve().parents[1] / "CIRCUITPY-MODERN" / "code.py"
tree = ast.parse(code_path.read_text(encoding="utf-8"))
selected = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "_LIGHT_ROUTE_COMMANDS"
        for target in node.targets
    ):
        selected.append(node)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
        "_light_route_lines", "_run_light_route"
    }:
        selected.append(node)

events = []

class Ctx:
    screen_w = 0
    screen_h = 0
    r = object()

    def raw(self, line):
        events.append(("raw", line))
        return "OK|RAW"

    def sleep_ms(self, milliseconds):
        events.append(("delay", milliseconds))
        return True

    def key_combo(self, *args): events.append(("key",) + args)
    def kdown(self, value): events.append(("down", value))
    def kup(self, value): events.append(("up", value))
    def beep(self, *args): events.append(("beep",) + args)

namespace = {
    "runtime": SimpleNamespace(random=SimpleNamespace(randint=lambda lo, hi: lo)),
    "_debug_event": lambda *args, **kwargs: None,
}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(code_path), "exec"), namespace)

route = """PLAN|2
SCREEN|1920,1080
SPEED|300,2000
RAW|MMOVE|94,-11,rel,2
DELAY|304
RAW|MMOVE|-82,148,rel,2
DELAY|185
"""
commands = namespace["_light_route_lines"](route)
assert commands is not None, "RAW/MMOVE hand path fell back to the full plan engine"
assert [command for command, _ in commands].count("RAW") == 2
ctx = Ctx()
namespace["_run_light_route"](ctx, commands)
assert events == [
    ("raw", "MMOVE|94,-11,rel,2"),
    ("delay", 304),
    ("raw", "MMOVE|-82,148,rel,2"),
    ("delay", 185),
], events
print("hand-sample light route: 5 passed, 0 failed")