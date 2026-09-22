#!/usr/bin/env python3
from pathlib import Path
import re

root = Path(__file__).resolve().parents[3]
exporter = (root / "ams-shell/src/Ams.UI/Services/PortableGuardBundle.cs").read_text(encoding="utf-8")

# The Combined Guard exporter must replace the legacy Pico README and metadata
# before SHA256SUMS is generated.
assert 'public const string ExporterVersion = "0.9.67"' in exporter
assert 'BuildPicoCalibrationMetadata(profiles, machine)' in exporter
assert 'BuildReadme(machine)' in exporter
assert exporter.index('BuildReadme(machine)') < exporter.index('var hashesPath = Path.Combine(directory, "SHA256SUMS.txt")')

# The generated operator guide must describe the complete package and must not
# reintroduce the removed adafruit_hid dependency or the old 9.x target.
assert "complete 24-file staging bundle" in exporter
assert "CircuitPython 10.3.0" in exporter
assert "Do not install or copy `adafruit_hid`" in exporter
assert "hardwareCalibrationVerified = false" in exporter
assert "Guard OFF" in exporter and "CALGET" in exporter
assert "Golden compatibility sidecars" in exporter
assert "CircuitPython 9.x" not in exporter
assert "پوشه‌ی `adafruit_hid`" not in exporter
assert 'generator = "Classroom Studio v" + ExporterVersion' in exporter

# Keep the inventory exact: 24 package files; SHA256SUMS hashes the 20 core payloads.
block = exporter.split('ExpectedBundleFiles = new[]', 1)[1].split('};', 1)[0]
files = re.findall(r'"([^"\\]+\.(?:py|txt|json|md|toml))"', block)
assert len(files) == 24, files
assert len(set(files)) == 24, files
for required in (
    "code.py", "boot.py", "combined_guard_runtime.py", "plan_engine.py",
    "live_light_guard.py", "guard_transition.py", "guard_calibration_protocol.py",
    "error_policy.py", "plan.txt", "guard-transition.json", "guard-calibration.json",
    "pico-calibration.json", "README-FLASH.md", "SHA256SUMS.txt",
    "desktop_steps.txt", "login_or_dc_steps.txt", "character_dashboard_steps.txt",
    "entering_game_loading_steps.txt", "game_steps.txt", "targeted_steps.txt",
    "resumable_steps.txt", "random_package_runtime.py", "settings.toml",
    "README-HID-TEST.txt",
):
    assert required in files, required

print("combined Guard export docs contract: current metadata, exact 24-file inventory, no legacy adafruit_hid/9.x instructions, and fail-closed calibration gate verified")
