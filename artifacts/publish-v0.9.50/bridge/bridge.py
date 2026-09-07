#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
bridge.py v2 — پل stdio بین پوسته WPF و استک پایتون AMS (مسیر B — بخش ۱۳.۱۰ سند طراحی)

تفاوت v2 (۰.۶.۲): نخ کارگر جداگانه برای اجرای فرمان‌ها + عملیات فوری «abort».
پیش از این، حلقهٔ stdin هنگام فرمان‌های طولانی (مثل WSND با پنجرهٔ ۲۰ ثانیه‌ای)
قفل می‌شد و HALTِ دکمهٔ Stop نمی‌توانست به برد برسد ← اسکریپت می‌ایستاد ولی
dokme Run دوباره فعال نمی‌شد.

پروتکل: JSON خط‌به‌خط روی stdin/stdout
  → {"op":"connect","port":"COM5"}      ← {"event":"connected","port":"COM5","fw":"1.6"}
  → {"op":"send","cmd":"MCLICK|left,1"} ← {"event":"reply","reply":"OK|MCLICK"}
  → {"op":"abort"}                      ← {"event":"abort_sent"}   (فوری — صف را دور می‌زند)
  → {"op":"send_path","pts":"x,y;x,y;…","dlys":"d;d;…"}  ← {"event":"reply","reply":"OK|PATH,n"}
      v0.9.2 — مسیر متراکم موس در یک عملیات واحد: نوشتن بدون انتظارِ پاسخ هر نقطه
      (تخلیهٔ پاسخ‌ها با PING هر ۱۲ نقطه) تا حرکت با کادانس واقعی دست (~۵ms / ~۳px) نرم باشد.
      فرمانِ در حال اجرا سپس با           ← {"event":"aborted","reply":"ERR|WSND|aborted"}
      رویداد aborted (نه reply) تمام می‌شود تا جفت‌کردن پاسخ‌ها سمت WPF به‌هم نریزد.
  → {"op":"disconnect"}                  ← {"event":"disconnected"}  (HALT + BYE — §۱۱.۳)
  → {"op":"ping_bridge"}                 ← {"event":"pong"}
رویدادهای EVT برد به‌صورت خودکار:          ← {"event":"evt","line":"EVT|..."}
خطاها:                                     ← {"event":"error","op":"...","message":"..."}

نکتهٔ هم‌زمانی: abort فقط روی پورت «می‌نویسد» (link._send) و هرگز نمی‌خواند —
خواندن فقط در نخ کارگر است (ams_serial قفل داخلی ندارد؛ دو خوانندهٔ هم‌زمان
روی یک پورت = دزدیده‌شدن پاسخ‌ها). نوشتن هم‌زمان حین خواندنِ مسدود، مسیر امن
pyserial است.

اجرا:
  python bridge.py --pydir "C:\Users\wasteland\Documents\ams\pc"
  (--pydir = پوشه‌ای که ams_serial.py و ams_crypto.py در آن است)
"""
import argparse
import json
import queue
import sys
import threading
import time

PRINT_LOCK = threading.Lock()


def emit(obj):
    with PRINT_LOCK:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def detect_board_port():
    """v0.9.5 — شناسایی خودکار برد: اسکن پورت‌های سریال، امتیاز به چیپ‌های شناخته‌شده
    (CH340/CP210x/FTDI/Arduino) و کاوش با PING؛ اولین پاسخ‌دهنده برمی‌گردد."""
    try:
        from serial.tools import list_ports
        import serial
    except Exception:
        return None
    KNOWN = {(0x1A86, 0x7523), (0x1A86, 0x5523), (0x0403, 0x6001), (0x10C4, 0xEA60),
             (0x2341, 0x0043), (0x2341, 0x0001), (0x2A03, 0x0043)}
    KEYS = ("ch340", "ch341", "usb-serial", "usb serial", "arduino", "cp210", "ftdi", "uart")
    def score(p):
        s = 0
        if (p.vid, p.pid) in KNOWN: s += 100
        d = ((p.description or "") + " " + (p.manufacturer or "")).lower()
        if any(k in d for k in KEYS): s += 50
        return s
    cands = sorted(list_ports.comports(), key=score, reverse=True)
    for p in cands:
        try:
            ser = serial.Serial(p.device, 115200, timeout=0.4, write_timeout=0.4)
            try:
                ser.reset_input_buffer(); ser.reset_output_buffer()
                ser.write(b"PING\n"); ser.flush()
                t0 = time.monotonic(); buf = b""
                while time.monotonic() - t0 < 0.8:
                    buf += ser.read(64)
                    if b"PONG" in buf or b"HELLO" in buf or b"OK" in buf:
                        return p.device
                    if not buf or len(buf) < 1:
                        time.sleep(0.02)
            finally:
                ser.close()
        except Exception:
            continue
    return cands[0].device if cands and score(cands[0]) >= 50 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pydir", default=".",
                    help="پوشه حاوی ams_serial.py و ams_crypto.py")
    args = ap.parse_args()
    sys.path.insert(0, args.pydir)

    from ams_serial import BoardLink, BoardError  # noqa: F401

    state = {"link": None}
    ops = queue.Queue()
    abort_flag = threading.Event()   # وقتی abort برای فرمانِ در حال اجرا فرستاده شد
    stop_evt = threading.Event()

    # ── نخ رویدادهای EVT برد ────────────────────────────────────────
    def event_pump():
        seen = 0
        while not stop_evt.is_set():
            link = state["link"]
            if link is not None:
                evs = link.events
                while seen < len(evs):
                    emit({"event": "evt", "line": evs[seen]})
                    seen += 1
            time.sleep(0.05)

    threading.Thread(target=event_pump, daemon=True).start()

    # ── نخ کارگر: اجرای ترتیبی همهٔ عملیات‌ها ─────────────────────────
    def worker():
        while True:
            req = ops.get()
            if req is None:                      # سم پایان
                return
            op = req.get("op")
            try:
                if op == "connect":
                    port = req.get("port") or "AUTO"
                    if port.strip().upper() in ("AUTO", ""):
                        port = detect_board_port() or "AUTO"   # v0.9.5 — اسکن خودکار
                    link = BoardLink(port=port)
                    dev = link.connect()
                    state["link"] = link
                    emit({"event": "connected", "port": dev, "fw": link.fw_ver})

                elif op == "list_ports":
                    # v0.9.43 — اتصال دستی: فهرست پورت‌های واقعی تا کاربر پورت پیکو را خودش انتخاب کند
                    try:
                        from serial.tools import list_ports as _lp
                        emit({"event": "ports", "ports": [
                            {"device": p.device, "label": p.description or ""}
                            for p in _lp.comports()
                        ]})
                    except Exception as ex:
                        emit({"event": "ports", "ports": [], "error": str(ex)})

                elif op == "send":
                    link = state["link"]
                    if link is None:
                        raise BoardError("not connected")
                    cmd = req["cmd"]
                    abort_flag.clear()
                    reply = link.command(cmd, timeout=req.get("timeout", 5.0))
                    if abort_flag.is_set():
                        # پاسخِ فرمانِ متوقف‌شده reply نمی‌شود تا جفت‌کردن
                        # پاسخ‌ها در سمت WPF به‌هم نریزد (انتظار قبلی cancel شده).
                        emit({"event": "aborted", "reply": reply, "cmd": cmd})
                    else:
                        emit({"event": "reply", "reply": reply})

                elif op == "send_path":
                    # v0.9.2 — استریم مسیر متراکم موس: MMOVE برای هر میکرواستپ بدون انتظار
                    # پاسخ (write-only) + PING هر ۱۲ نقطه برای تخلیهٔ بافر پاسخ‌ها. یک reply
                    # در انتها جفت‌کردن سمت WPF را حفظ می‌کند. abort بین نقاط چک می‌شود.
                    link = state["link"]
                    if link is None:
                        raise BoardError("not connected")
                    abort_flag.clear()
                    pts = [p for p in req.get("pts", "").split(";") if p]
                    dlys = [int(d) for d in req.get("dlys", "").split(";") if d]
                    if not pts:
                        raise BoardError("empty path")
                    send = getattr(link, "_send", None)
                    if send is None:
                        raise BoardError("bridge: _send unavailable")
                    aborted = False
                    t0 = time.monotonic()
                    budget = 0.0   # pacing تطبیقی: زمان هدف انباشته می‌شود، خواب فقط به اندازهٔ عقب‌ماندگی
                    for i, p in enumerate(pts):
                        if abort_flag.is_set():
                            aborted = True
                            break
                        send("MMOVE|" + p + ",abs,0")
                        if i % 12 == 11:
                            try:
                                link.command("PING", timeout=2.0)   # تخلیهٔ OK|MMOVEهای انباشته
                            except Exception:
                                pass
                        if i < len(dlys):
                            budget += dlys[i] / 1000.0
                            wait = t0 + budget - time.monotonic()
                            if wait > 0:
                                time.sleep(wait)
                    try:
                        link.command("PING", timeout=3.0)   # sync/tخلیهٔ نهایی
                    except Exception:
                        pass
                    if aborted or abort_flag.is_set():
                        emit({"event": "aborted", "reply": "ERR|PATH|aborted", "cmd": "send_path"})
                    else:
                        emit({"event": "reply", "reply": f"OK|PATH,{len(pts)}"})

                elif op == "disconnect":
                    link = state["link"]
                    if link is not None:
                        link.close()             # HALT + BYE + close (§۱۱.۳)
                        state["link"] = None
                    emit({"event": "disconnected"})

                elif op == "ping_bridge":
                    emit({"event": "pong"})

                else:
                    emit({"event": "error", "op": op, "message": "unknown op"})
            except Exception as e:
                if op in ("send", "send_path") and abort_flag.is_set():
                    emit({"event": "aborted", "reply": "ERR|aborted", "cmd": req.get("cmd")})
                else:
                    emit({"event": "error", "op": op, "message": str(e)})

    threading.Thread(target=worker, daemon=True).start()

    # ── حلقهٔ اصلی stdin — abort همین‌جا و فوری پاسخ داده می‌شود ─────
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            emit({"event": "error", "message": "bad json"})
            continue

        if req.get("op") == "abort":
            handle_abort(state, abort_flag)
        else:
            ops.put(req)

    stop_evt.set()
    ops.put(None)


def handle_abort(state, abort_flag):
    """HALT را فوری روی پورت «می‌نویسد» تا گوش‌به‌زنگ/فرمان طولانی برد بشکند.

    فقط نوشتن — خواندن پاسخ بر عهدهٔ نخ کارگر است (دو خوانندهٔ هم‌زمان ممنوع).
    """
    link = state["link"]
    abort_flag.set()
    if link is None:
        emit({"event": "abort_sent", "note": "not connected"})
        return

    def _write_halt():
        try:
            send = getattr(link, "_send", None)
            if send is not None:
                send("HALT")                 # فقط نوشتن — بدون خواندن
            else:
                link.halt()                  # fallback برای ams_serial قدیمی
        except Exception:
            pass

    threading.Thread(target=_write_halt, daemon=True).start()
    emit({"event": "abort_sent"})


if __name__ == "__main__":
    main()
