"""CI smoke test: the bridge must START and answer ping_bridge with pong on a clean
machine. Catches what py_compile cannot: missing imports (e.g. the v0.9.57 missing
`import os`), unvendored dependencies, and startup crashes.

Deterministic: stdin is HELD OPEN for 2s after the ping so the bridge's worker
thread has time to print pong before EOF would end the process (one-shot pipe
races were the false-failure mode of the inline pwsh smoke)."""
import subprocess
import sys
import threading
import time

p = subprocess.Popen(
    [sys.executable, "ams-shell/bridge/bridge.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True,
)

def feed():
    try:
        p.stdin.write('{"op":"ping_bridge"}\n')
        p.stdin.flush()
        time.sleep(2.0)   # hold stdin open: worker needs a beat to answer
    finally:
        try:
            p.stdin.close()

threading.Thread(target=feed).start()
killer = threading.Timer(30, p.kill)   # never let CI hang
killer.start()
out = p.stdout.read()
killer.cancel()

with open("smoke-output.txt", "w") as fh:
    fh.write(out)
sys.stdout.write(out)
sys.exit(0 if '"pong"' in out else 1)
