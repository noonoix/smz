#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Low-latency launcher for the proven Classroom Studio bridge.

The Pico DATA link originally kept pyserial's 200 ms read timeout after the
handshake. Pico replies are short, while PicoLink._read_line reads up to 64
bytes, so each command reply commonly waited for the whole 200 ms timeout.
That transport wait was added between separate KDOWN/KUP steps and could hold
a key long enough to trigger Windows auto-repeat.

Keep bridge_core.py completely intact and only reduce the post-handshake Pico
read timeout to 10 ms. Command ACKs, ordering, error reporting, cancellation,
and the direct-Pro-Micro encrypted path therefore remain unchanged.
"""
import bridge_core as core

PICO_COMMAND_READ_TIMEOUT_S = 0.01
_original_pico_connect = core.PicoLink.connect


def _connect_with_low_latency_reads(self):
    device = _original_pico_connect(self)
    if self.ser is not None:
        self.ser.timeout = PICO_COMMAND_READ_TIMEOUT_S
    return device


core.PicoLink.connect = _connect_with_low_latency_reads

if __name__ == "__main__":
    core.main()
