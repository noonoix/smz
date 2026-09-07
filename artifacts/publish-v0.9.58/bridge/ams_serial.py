# -*- coding: utf-8 -*-
"""
ams_serial.py — لینک سریال رمزشده با برد AMS (سمت PC)
- handshake با چالش nonce (اثبات دوطرفه کلید)
- قاب‌های E|<n>|<hex> با شمارنده ضد-replay
- رویدادهای EVT از برد (مثل شلیک TRGSND) در صف events می‌نشینند
"""
import os
import time

from ams_crypto import Session, load_psk

KNOWN_VIDS = {0x2341, 0x1B4F, 0x2A03, 0x239A}   # Arduino / SparkFun / clones


class BoardError(Exception):
    pass


class BoardLink:
    def __init__(self, psk=None, port="AUTO", baud=115200, settle_s=2.5):
        self.psk = psk if psk is not None else load_psk()
        self.port = port
        self.baud = baud
        self.settle_s = settle_s
        self.ser = None
        self.session = None
        self.tx = 0
        self.rx = 0
        self.events = []          # لیست خطوط EVT دریافتی
        self.fw_ver = None
        self.gaps = 0             # پاسخ‌های گم‌شدهٔ لورفته با پرش شمارنده
        self.stale = 0            # پاسخ‌های دیرهنگامِ فرمان قبلی
        self.resyncs = 0          # تعداد همگام‌سازی پس از گم شدن پاسخ
        self._rxbuf = bytearray()  # بایت‌های خطِ نیمه‌تمام بین دو فراخوانی
        self.dupes = 0            # قاب‌های تکراری دورریخته
        self.partials = 0         # دفعاتی که خط هنگام پایان پنجره نیمه‌تمام بود

    # ---------- اتصال ----------
    def connect(self):
        import serial
        from serial.tools import list_ports

        candidates = []
        if self.port != "AUTO":
            candidates = [self.port]
        else:
            ports = list(list_ports.comports())
            known = [p.device for p in ports if p.vid in KNOWN_VIDS]
            others = [p.device for p in ports if p.vid not in KNOWN_VIDS]
            candidates = known + others
        if not candidates:
            raise BoardError("هیچ پورت سریالی پیدا نشد — برد وصل است؟")

        last_err = None
        for dev in candidates:
            try:
                self.ser = serial.Serial(dev, self.baud, timeout=0.2, write_timeout=2)
                time.sleep(self.settle_s)          # ریست برد بعد از باز شدن پورت (سبک Leonardo)
                self._reset_input()
                self._handshake()
                self.port = dev
                return dev
            except Exception as e:
                last_err = e
                try:
                    if self.ser:
                        self.ser.close()
                except Exception:
                    pass
                self.ser = None
        raise BoardError("handshake روی هیچ پورتی موفق نشد: %s" % last_err)

    def _handshake(self, attempts=3):
        """HELLO را تا چند بار تکرار می‌کند.

        برد ممکن است از اجرای قبلی در حالت نشستِ باز مانده باشد (Pro Micro با
        باز شدن پورت ریست نمی‌شود)؛ فریم‌ور ۱.۳+ با دیدن HELLO نشست تازه
        می‌سازد، پس تکرار درخواست مشکل را بدون قطع/وصل حل می‌کند.
        """
        last_err = "به HELLO پاسخی نیامد"
        for _ in range(max(1, attempts)):
            nonce = os.urandom(16)
            sess = Session(self.psk, nonce)
            self._reset_input()
            self._write_line("HELLO|" + nonce.hex().upper())
            deadline = time.time() + 1.5
            while time.time() < deadline:
                line = self._read_line(0.3)
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) == 5 and parts[0] == "OK" and parts[1] == "HELLO":
                    if parts[2] != "AMS_BOARD":
                        raise BoardError("پاسخHELLO نامعتبر: %s" % line)
                    if parts[4].strip().upper() != sess.proof_hex():
                        raise BoardError("اثبات کلید برد نامعتبر است — PSK یکسان نیست؟")
                    self.session = sess
                    self.fw_ver = parts[3]
                    self.tx = 0
                    self.rx = 0
                    return
        raise BoardError(last_err)

    # ---------- قاب ----------
    def _write_line(self, text):
        self.ser.write(text.encode("ascii") + b"\n")
        self.ser.flush()

    def _read_line(self, timeout=0.5):
        """یک خط کامل برمی‌گرداند؛ بایت‌های نیمه‌تمام دور ریخته نمی‌شوند.

        نسخهٔ قبلی بافر محلی داشت و اگر مهلتش در میانهٔ یک خط تمام می‌شد،
        نیمهٔ اول را می‌ریخت و نیمهٔ دوم به‌عنوان خطی بی‌معنی برگشت می‌خورد — یعنی
        یک قاب کاملاً سالم فقط به خاطر محل برش پکت USB نابود می‌شد.
        """
        end = time.time() + timeout
        while True:
            nl = self._rxbuf.find(b"\n")
            if nl >= 0:
                raw = bytes(self._rxbuf[:nl])
                del self._rxbuf[:nl + 1]
                text = raw.decode("ascii", errors="replace").strip()
                if text:
                    return text
                continue
            if time.time() >= end:
                if self._rxbuf:
                    self.partials += 1
                return None
            try:
                waiting = self.ser.in_waiting
            except Exception:
                waiting = 0
            chunk = self.ser.read(waiting if waiting > 0 else 1)
            if chunk:
                self._rxbuf += chunk

    def _reset_input(self):
        """بافر سختی و بافر نرمِ خط را با هم خالی می‌کند."""
        self._rxbuf = bytearray()
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

    def _send(self, text):
        self.tx += 1
        self._write_line(self.session.encrypt_frame(self.tx, text))

    def _recv(self, timeout=5.0, expect_name=None):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._read_line(0.3)
            if not line:
                continue
            n, plain = self.session.decrypt_frame(line)
            if plain is None:
                continue
            # ضد-replay فقط به «اکیداً صعودی» نیاز دارد: شمارندهٔ مساوی یا
            # عقب‌تر همان replay است و رد می‌شود، اما شمارندهٔ جلوتر یعنی یک
            # پاسخ در راه گم شده؛ پذیرشش هم امن است هم لینک را زنده نگه
            # می‌دارد. قاعدهٔ «دقیقاً +۱» با یک قاب گم‌شده نشست را می‌کشت.
            if n == self.rx:
                # دوباره‌فرستی همان قاب، بی‌ضرر است: قبلاً پردازش شده، پس دور
                # ریختنش امن‌تر از کشتن نشست است (فرمور ۱.۶ در صورت افتادن نوشتن CDC تکرار می‌کند).
                self.dupes += 1
                continue
            if n < self.rx:
                raise BoardError(
                    "شمارنده قاب عقب‌افتاده (replay?) — دریافت %d، آخرین %d"
                    % (n, self.rx)
                )
            if n > self.rx + 1:
                self.gaps += n - (self.rx + 1)
            self.rx = n
            if plain.startswith("EVT|"):
                self.events.append(plain)
                continue
            # پاسخ دیرهنگامِ فرمان قبلی نباید به حساب فرمان جاری نوشته شود
            if expect_name and plain.startswith("OK|"):
                parts = plain.split("|")
                if len(parts) >= 2 and parts[1] and parts[1] != expect_name:
                    self.stale += 1
                    continue
            return plain
        raise BoardError("مهلت دریافت پاسخ از برد تمام شد")

    def resync(self, window=0.8):
        """قاب‌های عقب‌مانده را می‌خورد تا شمارندهٔ دریافت به‌روز شود.

        بدون این، یک پاسخ گم‌شده باعث می‌شود همهٔ فرمان‌های بعدی با خطای
        شمارنده رد شوند. تعداد پاسخ دورریخته را برمی‌گرداند.
        """
        dropped = 0
        end = time.time() + window
        while time.time() < end:
            line = self._read_line(0.2)
            if not line:
                continue
            try:
                n, plain = self.session.decrypt_frame(line)
            except Exception:
                continue
            if plain is None:
                continue
            if n > self.rx:
                self.rx = n
            if plain.startswith("EVT|"):
                self.events.append(plain)
            else:
                dropped += 1
        self.resyncs += 1
        return dropped

    # ---------- API ----------
    def command(self, text, timeout=5.0, resync=True):
        """یک فرمان می‌فرستد و پاسخ OK/ERR را برمی‌گرداند.

        اگر پاسخ نرسید، پیش از پرتاب خطا لینک را همگام می‌کند تا فرمان بعدی
        قربانیِ قاب گم‌شده نشود.
        """
        self._send(text)
        name = text.split("|", 1)[0].strip()
        try:
            return self._recv(timeout, expect_name=name)
        except BoardError:
            if resync:
                try:
                    self.resync()
                except Exception:
                    pass
            raise

    def halt(self):
        try:
            return self.command("HALT", timeout=2)
        except Exception:
            return None

    def bye(self):
        """نشست را روی برد می‌بندد تا اجرای بعدی تمیز handshake کند (فریم‌ور ۱.۳+)."""
        try:
            return self.command("BYE", timeout=2)
        except Exception:
            return None

    def close(self):
        try:
            self.halt()
            self.bye()
        finally:
            self.session = None
            if self.ser:
                self.ser.close()
                self.ser = None
