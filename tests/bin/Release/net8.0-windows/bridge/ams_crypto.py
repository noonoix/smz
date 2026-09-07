# -*- coding: utf-8 -*-
"""
ams_crypto.py — AES-128 + قاب‌بندی نشست برای کانال فرمان AMS (سمت PC)
دقیقاً مطابق فریم‌ور ams_board.ino:
  - PSK شانزده‌بایتی مشترک (ams_key.json / ams_key.h)
  - handshake: proof = AES128(PSK, nonce)  →  session key = proof
  - قاب nام (در هر جهت، از ۱ شروع می‌شود):
      ctrBlock = nonce[0:6] || BE64(n) || BE16(j)   برای تکه jام از متن
      ciphertext = plaintext XOR AES128(sessionKey, ctrBlock)
  - روی خط:  E|<n>|<hex>
اگر pycryptodome نصب باشد از آن استفاده می‌شود، وگرنه پیاده‌سازی خالص پایتون.
"""
import os

# ---------------- AES-128 خالص پایتون (فقط encrypt — CTR) ----------------
SBOX = (
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
)

def _xtime(x):
    return ((x << 1) ^ (0x1B if x & 0x80 else 0)) & 0xFF


def _shift_rows(s):
    o = s
    return [o[0], o[5], o[10], o[15],
            o[4], o[9], o[14], o[3],
            o[8], o[13], o[2], o[7],
            o[12], o[1], o[6], o[11]]


class _AesPure:
    __slots__ = ("rk",)

    def __init__(self, key: bytes):
        assert len(key) == 16
        rk = bytearray(key)
        rcon = 1
        while len(rk) < 176:
            t = list(rk[-4:])
            if len(rk) % 16 == 0:
                t = [SBOX[t[1]], SBOX[t[2]], SBOX[t[3]], SBOX[t[0]]]
                t[0] ^= rcon
                rcon = _xtime(rcon)
            for i in range(4):
                rk.append(rk[-16] ^ t[i])
        self.rk = bytes(rk)

    def encrypt(self, block: bytes) -> bytes:
        assert len(block) == 16
        rk = self.rk
        s = [b ^ k for b, k in zip(block, rk[:16])]
        for rnd in range(1, 10):
            s = [SBOX[x] for x in s]
            s = _shift_rows(s)
            ns = []
            for c in range(4):
                a0, a1, a2, a3 = s[4*c:4*c+4]
                ns += [
                    _xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3,
                    a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3,
                    a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3),
                    (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3),
                ]
            s = [x ^ k for x, k in zip(ns, rk[rnd*16:(rnd+1)*16])]
        s = [SBOX[x] for x in s]
        s = _shift_rows(s)
        s = [x ^ k for x, k in zip(s, rk[160:176])]
        return bytes(s)


# ---------- مسیر سریع با pycryptodome در صورت وجود ----------
try:
    from Crypto.Cipher import AES as _CAES  # type: ignore
    _FAST = True
except Exception:
    _FAST = False


def aes128_encrypt(key: bytes, block: bytes) -> bytes:
    if _FAST:
        return _CAES.new(key, _CAES.MODE_ECB).encrypt(block)
    return _AesPure(key).encrypt(block)


def load_psk(path=None) -> bytes:
    """PSK را از ams_key.json می‌خواند (یا از متغیر محیطی AMS_PSK به صورت hex)."""
    env = os.environ.get("AMS_PSK")
    if env:
        return bytes.fromhex(env.strip())
    import json
    here = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "ams_key.json")
    with open(here, encoding="utf-8") as f:
        return bytes.fromhex(json.load(f)["psk_hex"])


# ---------------- نشست ----------------
class Session:
    """نشست رمزشده دوطرفه؛ شمارنده‌ها در هر جهت مستقل و از ۱ شروع می‌شوند."""

    def __init__(self, psk: bytes, nonce: bytes):
        assert len(psk) == 16 and len(nonce) == 16
        self.psk = psk
        self.nonce = nonce
        self.key = aes128_encrypt(psk, nonce)   # session key = proof
        self._aes = None if _FAST else _AesPure(self.key)

    def proof_hex(self) -> str:
        return self.key.hex().upper()

    def _ks(self, n: int, j: int) -> bytes:
        ctr = self.nonce[:6] + n.to_bytes(8, "big") + j.to_bytes(2, "big")
        if self._aes is not None:
            return self._aes.encrypt(ctr)
        return aes128_encrypt(self.key, ctr)

    def crypt(self, n: int, data: bytes) -> bytes:
        out = bytearray()
        for off in range(0, len(data), 16):
            ks = self._ks(n, off // 16)
            chunk = data[off:off + 16]
            out += bytes(a ^ b for a, b in zip(chunk, ks))
        return bytes(out)

    def encrypt_frame(self, n: int, text: str) -> str:
        pt = text.encode("utf-8")
        pad = (-len(pt)) % 16
        pt += b"\x00" * pad
        ct = self.crypt(n, pt)
        return "E|%d|%s" % (n, ct.hex().upper())

    def decrypt_frame(self, line: str):
        if not line.startswith("E|"):
            return None, None
        try:
            _, n_s, hex_s = line.split("|", 2)
            n = int(n_s)
            ct = bytes.fromhex(hex_s)
        except ValueError:
            return None, None
        if not ct or len(ct) % 16:
            return None, None
        pt = self.crypt(n, ct).rstrip(b"\x00")
        return n, pt.decode("utf-8", errors="replace")
