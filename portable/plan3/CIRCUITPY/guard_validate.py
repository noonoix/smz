# First-stage Guard validator. Keep this module small: it is discarded by
# supervisor.reload() before guard_main.py and the executor are imported.
import gc
import sys
import os as _real_os
import hashlib as _real_hashlib

class _PathCompat:
    @staticmethod
    def join(root, name):
        if not root or root == "/": return "/" + name.lstrip("/")
        return root.rstrip("/") + "/" + name.lstrip("/")
    @staticmethod
    def isfile(path):
        try: return (_real_os.stat(path)[0] & 0x4000) == 0
        except OSError: return False

class _OsCompat:
    path = _PathCompat()
    def __getattr__(self, name): return getattr(_real_os, name)

if not hasattr(_real_os, "path"):
    sys.modules["os"] = _OsCompat()

class _Sha256Compat:
    def __init__(self, data=None):
        self.hash = _real_hashlib.new("sha256")
        if data: self.hash.update(data)
    def update(self, data): self.hash.update(data)
    def digest(self): return self.hash.digest()
    def hexdigest(self): return "".join("%02x" % byte for byte in self.hash.digest())

class _HashlibCompat:
    def sha256(self, data=None): return _Sha256Compat(data)
    def __getattr__(self, name): return getattr(_real_hashlib, name)

if not hasattr(_real_hashlib, "sha256"):
    sys.modules["hashlib"] = _HashlibCompat()

import live_light_guard as _guard
for _name in ("pico-calibration.json", "README-FLASH.md", "guard_main.py", "guard_validate.py"):
    if _name not in _guard.HASHED_BUNDLE_FILES:
        _guard.HASHED_BUNDLE_FILES += (_name,)

def run():
    _guard.load_guard_bundle("/", verify=True)
    gc.collect()
