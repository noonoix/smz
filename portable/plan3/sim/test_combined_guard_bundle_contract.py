#!/usr/bin/env python3
"""Offline preflight contract for the combined Guard CIRCUITPY bundle."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "portable/plan3/CIRCUITPY"))
from live_light_guard import (
    GuardBundleError,
    HASHED_BUNDLE_FILES,
    OPTIONAL_COMPATIBILITY_SIDECARS,
    LightStateGuard,
    REQUIRED_BUNDLE_FILES,
    ROUTE_FILES,
    load_guard_bundle,
)

PROFILE_IDS = (
    "desktop",
    "login-or-dc",
    "character-dashboard",
    "entering-game-loading",
    "game",
    "targeted",
)
REVISION = "guard-offline-test"


def refresh_hashes(path):
    lines = []
    for filename in sorted(set(HASHED_BUNDLE_FILES)):
        digest = hashlib.sha256((path / filename).read_bytes()).hexdigest()
        lines.append(digest + "  " + filename)
    (path / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bundle(path):
    profiles = []
    calibration_profiles = {}
    for index, profile_id in enumerate(PROFILE_IDS):
        center = 10.0 + index * 10
        profile = {"id": profile_id, "center": center, "tolerance": 2.0, "stableMs": 750}
        profiles.append(profile)
        calibration_profiles[profile_id] = {"center": center, "tolerance": 2.0, "stable_ms": 750}
    manifest = {
        "format": 1,
        "runtime": "combined-pico-guard-executor",
        "calibrationRevision": REVISION,
        "routes": ROUTE_FILES,
        "profiles": profiles,
    }
    calibration = {"format": 1, "revision": REVISION, "profiles": calibration_profiles}
    (path / "guard-transition.json").write_text(json.dumps(manifest), encoding="utf-8")
    (path / "guard-calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
    for filename in ROUTE_FILES.values():
        (path / filename).write_text("PLAN|2\n", encoding="utf-8")
    for filename in REQUIRED_BUNDLE_FILES:
        (path / filename).write_text("# offline preflight placeholder\n", encoding="utf-8")
    refresh_hashes(path)


def expect_rejected(path, label):
    try:
        load_guard_bundle(str(path))
    except GuardBundleError:
        return
    raise AssertionError("bundle was accepted: " + label)


with tempfile.TemporaryDirectory() as temporary:
    bundle = Path(temporary)
    write_bundle(bundle)
    loaded = load_guard_bundle(str(bundle))
    assert loaded["revision"] == REVISION
    assert len(loaded["states"]) == 6
    assert len({state["id"] for state in loaded["states"]}) == 6
    assert len(ROUTE_FILES) == 8
    assert isinstance(LightStateGuard.from_bundle(str(bundle)), LightStateGuard)

    # Older Classroom Studio exports included the three Random Package
    # compatibility sidecars in SHA256SUMS.txt. They must remain bootable while
    # new exports keep them outside the Golden manifest.
    sidecar_lines = []
    for filename in OPTIONAL_COMPATIBILITY_SIDECARS:
        payload = (Path(filename).name + "\n").encode()
        (bundle / filename).write_bytes(payload)
        sidecar_lines.append(hashlib.sha256(payload).hexdigest() + "  " + filename)
    with (bundle / "SHA256SUMS.txt").open("a", encoding="utf-8") as manifest_file:
        manifest_file.write("\n".join(sidecar_lines) + "\n")
    loaded_compat = load_guard_bundle(str(bundle))
    assert loaded_compat["revision"] == REVISION

    manifest_path = bundle / "guard-transition.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["profiles"].append(dict(manifest["profiles"][0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    expect_rejected(bundle, "duplicate optical profile")

    write_bundle(bundle)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["calibrationRevision"] = "stale-revision"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    expect_rejected(bundle, "manifest/calibration revision mismatch")

    write_bundle(bundle)
    calibration_path = bundle / "guard-calibration.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    calibration["profiles"]["game"]["tolerance"] = 99
    calibration_path.write_text(json.dumps(calibration), encoding="utf-8")
    expect_rejected(bundle, "profile value mismatch")

    write_bundle(bundle)
    (bundle / ROUTE_FILES["Resumable"]).unlink()
    expect_rejected(bundle, "missing Resumable route")

    write_bundle(bundle)
    (bundle / "plan_engine.py").unlink()
    expect_rejected(bundle, "missing plan engine")

    write_bundle(bundle)
    (bundle / ROUTE_FILES["Game"]).write_text("tampered\n", encoding="utf-8")
    expect_rejected(bundle, "tampered route hash")

print("combined Guard bundle preflight: exact six profiles, seven routes, runtime completeness, SHA256 integrity, revision parity and fail-closed rejection verified")
