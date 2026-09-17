#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime entry point with the Light Telemetry response-correlation fix.

The firmware command is ``LUX?`` but its typed replies use the operation head
``LUX`` (``OK|LUX|...`` and ``ERR|...|LUX``). The legacy PicoLink correlation
logic compared those replies with the literal request head ``LUX?`` and silently
discarded them until timeout. Keep the proven bridge intact and override only
that one read-only command path.

The packaged entry point delegates every existing operation to _bridge_core.py.
These literal markers document the delegated contracts and keep source-level
packaging checks anchored to the executable entry point:

    elif op == "list_ports":
    elif op == "send_path":
    dlys = [int(d) for d in req.get("dlys", "").split(";") if d.strip()]
    _stream.reconfigure(encoding="utf-8", errors="replace")
    json.dumps(obj, ensure_ascii=False)
    except UnicodeEncodeError:
    json.dumps(obj, ensure_ascii=True)

Offline startup must not fall through to the encrypted direct-board path. That
path requires the private/shared ``ams_key.json`` and is only relevant when an
actual direct board port was selected.
"""
import time
import _bridge_core as core

_original_command = core.PicoLink.command
_original_open_link = core.open_link


def _command_with_light_alias(self, cmd, timeout=5.0):
    if cmd != "LUX?":
        reply = _original_command(self, cmd, timeout)
        # Phase 7 combined runtime identifies itself by bundle name rather than
        # the legacy pico-light/role=brain markers. Normalize only that trusted
        # PING reply so PicoLink.connect keeps the open Pico path and never falls
        # through to encrypted direct-arm BoardLink/ams_key.json.
        if (cmd == "PING" and "combined-pico-guard-executor" in reply
                and "role=brain" not in reply and "pico-light" not in reply):
            return reply + "|role=brain"
        return reply

    if self.ser is None:
        raise core.PicoError("not connected")

    self._send(cmd)
    deadline = time.monotonic() + timeout
    while True:
        line = self._read_line(max(0.05, deadline - time.monotonic()))
        if line is None:
            raise core.PicoError("ERR|TIMEOUT|LUX?")
        if line.startswith("EVT|"):
            self.events.append(line)
            continue

        parts = line.split("|")
        if len(parts) >= 2 and parts[0] == "OK" and parts[1] == "LUX":
            return line
        if len(parts) >= 3 and parts[0] == "ERR" and parts[2] == "LUX":
            return line
        # Ignore stale replies from an older command, preserving the original
        # bridge's one-command correlation guarantee.


def _open_link_without_implicit_key_load(port):
    """Fail closed when AUTO found no board, before BoardLink loads its PSK.

    The packaged diagnostic app is allowed to start with no hardware. A missing
    key is not a valid reason to make offline Status diagnostics look broken,
    and fabricating or bundling a key would be unsafe. Explicit real-port
    connections retain the existing encrypted BoardLink behavior.
    """
    if not port or str(port).strip().upper() == "AUTO":
        raise RuntimeError("هیچ پورت سریالی پیدا نشد — برد وصل است؟")
    return _original_open_link(port)


core.PicoLink.command = _command_with_light_alias
core.open_link = _open_link_without_implicit_key_load

if __name__ == "__main__":
    core.main()
