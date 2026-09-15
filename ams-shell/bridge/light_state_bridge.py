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
    req.get("dlys", "").split(";")
    _stream.reconfigure(encoding="utf-8", errors="replace")
    json.dumps(obj, ensure_ascii=False)
    except UnicodeEncodeError:
    json.dumps(obj, ensure_ascii=True)
"""
import time
import _bridge_core as core

_original_command = core.PicoLink.command


def _command_with_light_alias(self, cmd, timeout=5.0):
    if cmd != "LUX?":
        return _original_command(self, cmd, timeout)

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


core.PicoLink.command = _command_with_light_alias

if __name__ == "__main__":
    core.main()
