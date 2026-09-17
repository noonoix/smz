#!/usr/bin/env python3
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types

root = Path(__file__).resolve().parents[3]
wrapper_path = root / "ams-shell/bridge/light_state_bridge.py"
runtime_path = root / "firmware/pico-light-guard-1.0.0/combined_guard_runtime.py"
wrapper_text = wrapper_path.read_text(encoding="utf-8")
runtime_text = runtime_path.read_text(encoding="utf-8")

assert 'combined-pico-guard-executor' in runtime_text
assert 'if line == "PING": reply = "OK|PONG|combined-pico-guard-executor' in runtime_text
assert 'reply + "|role=brain"' in wrapper_text
assert 'cmd == "PING" and "combined-pico-guard-executor" in reply' in wrapper_text

fake = types.ModuleType("_bridge_core")
class PicoError(Exception):
    pass
class PicoLink:
    def __init__(self, reply):
        self.reply = reply
        self.ser = object()
        self.events = []
    def command(self, cmd, timeout=5.0):
        return self.reply
fake.PicoError = PicoError
fake.PicoLink = PicoLink
fake.open_link = lambda port: port
fake.main = lambda: None
sys.modules["_bridge_core"] = fake
spec = spec_from_file_location("light_state_bridge_contract", wrapper_path)
module = module_from_spec(spec)
spec.loader.exec_module(module)

combined = PicoLink("OK|PONG|combined-pico-guard-executor|hid=on|uart=on|profiles=6")
reply = combined.command("PING")
assert reply.endswith("|role=brain"), reply
assert reply.count("role=brain") == 1
legacy = PicoLink("OK|PONG|pico-light 1.0|role=brain")
assert legacy.command("PING") == legacy.reply
other = PicoLink("OK|PONG|direct-arm")
assert other.command("PING") == other.reply

print("combined Guard bridge identity contract: PING normalized to Pico role without ams_key fallback")
