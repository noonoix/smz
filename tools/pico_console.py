#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pico_console.py — خواندن کنسول پیکو (پورت REPL) + ری‌استارت code.py برای دیدن traceback.

چرا: وقتی code.py هنگام بوت می‌میرد، traceback فقط روی پورت کنسول (معمولاً COM3) چاپ می‌شود،
نه پورت data. این ابزار پورت را باز می‌کند، Ctrl+C و Ctrl+D می‌فرستد تا code.py دوباره اجرا
شود و هر چه چاپ شد — از جمله traceback — همین‌جا نشان داده می‌شود.

اجرا (از پوشه‌ی ریلیز، جایی که پوشه‌ی bridge هست — pyserial همان‌جا bundled است):

    python tools\pico_console.py COM3

اگر پورت کنسولت COM3 نیست، همان پورتی را بده که در Device Manager اولین پورت پیکوست.
۲۰ ثانیه ضبط می‌کند و تمام می‌شود. خروجی را کپی کن و بفرست.
"""
import os
import sys
import time

# pyserial bundled کنار bridge/ در ریلیز قرار دارد
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.join(_HERE, "..", "bridge"), _HERE, os.path.join(_HERE, "..")):
    if os.path.isdir(os.path.join(_cand, "serial")):
        sys.path.insert(0, os.path.abspath(_cand))
        break

import serial  # noqa: E402


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
    ser = serial.Serial(port, 115200, timeout=0.1)
    print(f"[pico_console] {port} باز شد — Ctrl+C سپس Ctrl+D می‌رود تا code.py تازه اجرا شود…")
    ser.write(b"\x03")   # Ctrl+C — اجرای فعلی را بشکن (اگر گیر کرده)
    time.sleep(0.6)
    ser.write(b"\x04")   # Ctrl+D — soft reload: boot.py + code.py دوباره اجرا می‌شوند
    t0 = time.time()
    try:
        while time.time() - t0 < 20:
            chunk = ser.read(256)
            if chunk:
                sys.stdout.write(chunk.decode("utf-8", "replace"))
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    print("\n[pico_console] تمام شد — کل خروجی بالا را کپی کن و بفرست")


if __name__ == "__main__":
    main()
