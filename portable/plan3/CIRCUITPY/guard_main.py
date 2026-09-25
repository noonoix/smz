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


# The first-stage validator already performed the full hash scan. On the
# second interpreter lifetime, load only the structural bundle data and compact
# it before compiling the executor; this preserves a contiguous heap block for
# plan_engine's first import.
import live_light_guard as _guard
_BOOT_BUNDLE = _guard.load_guard_bundle("/", verify=False)
_manifest = _BOOT_BUNDLE["manifest"]
_calibration = _BOOT_BUNDLE["calibration"]
_profiles = []
for _item in _manifest.get("profiles", ()):
    _profiles.append({
        "id": _item["id"], "center": _item["center"],
        "tolerance": _item["tolerance"], "stableMs": _item["stableMs"]})
_calibration_profiles = {}
for _pid, _item in _calibration.get("profiles", {}).items():
    _calibration_profiles[_pid] = {
        "center": _item["center"], "tolerance": _item["tolerance"],
        "stable_ms": _item["stable_ms"]}
_BOOT_BUNDLE = {
    "manifest": {
        "format": _manifest.get("format"),
        "runtime": _manifest.get("runtime"),
        "calibrationRevision": _manifest.get("calibrationRevision"),
        "routes": dict(_manifest.get("routes", {})),
        "profiles": _profiles,
    },
    "calibration": {
        "format": _calibration.get("format"),
        "revision": _calibration.get("revision"),
        "profiles": _calibration_profiles,
    },
    "revision": _BOOT_BUNDLE["revision"],
    "states": _BOOT_BUNDLE["states"],
    "stable_ms": _BOOT_BUNDLE["stable_ms"],
    "hysteresis": _BOOT_BUNDLE["hysteresis"],
    "sensor_timeout_ms": _BOOT_BUNDLE["sensor_timeout_ms"],
}
del _manifest, _calibration, _profiles, _calibration_profiles, _guard
import gc
gc.collect()
import combined_guard_runtime as runtime
runtime._BOOT_BUNDLE = _BOOT_BUNDLE
del _BOOT_BUNDLE
runtime.main()
