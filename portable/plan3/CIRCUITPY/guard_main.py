# Second-stage Guard entry point.
# Keep this file intentionally tiny: the first stage already verified the bundle,
# and the executor owns the long-running loop.  Do not put debug/calibration
# wrappers here; importing them on RP2040 recreates the original heap failure.
import sys
import os as _real_os
import hashlib as _real_hashlib


class _PathCompat:
    @staticmethod
    def join(root, name):
        if not root or root == "/":
            return "/" + name.lstrip("/")
        return root.rstrip("/") + "/" + name.lstrip("/")

    @staticmethod
    def isfile(path):
        try:
            return (_real_os.stat(path)[0] & 0x4000) == 0
        except OSError:
            return False


class _OsCompat:
    path = _PathCompat()

    def __getattr__(self, name):
        return getattr(_real_os, name)


if not hasattr(_real_os, "path"):
    sys.modules["os"] = _OsCompat()


class _Sha256Compat:
    def __init__(self, data=None):
        self.hash = _real_hashlib.new("sha256")
        if data:
            self.hash.update(data)

    def update(self, data):
        self.hash.update(data)

    def digest(self):
        return self.hash.digest()

    def hexdigest(self):
        return "".join("%02x" % byte for byte in self.hash.digest())


class _HashlibCompat:
    def sha256(self, data=None):
        return _Sha256Compat(data)

    def __getattr__(self, name):
        return getattr(_real_hashlib, name)


if not hasattr(_real_hashlib, "sha256"):
    sys.modules["hashlib"] = _HashlibCompat()


import combined_guard_runtime as runtime
runtime.main()
