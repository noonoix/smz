import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CIRCUITPY"))
from live_light_guard import GuardBundleError, LightStateGuard, ROUTE_FILES, load_guard_bundle, state_spec


class LiveLightGuardTests(unittest.TestCase):
    def setUp(self):
        self.states = [
            state_spec("dark", 0, 100, "dark.plan.txt"),
            state_spec("bright", 160, 400, "bright.plan.txt"),
        ]

    def setUpCanonical(self):
        self.canonical = [
            state_spec("desktop", 0, 10, "desktop_steps.txt"),
            state_spec("login-or-dc", 20, 30, "login_or_dc_steps.txt"),
            state_spec("character-dashboard", 40, 50, "character_dashboard_steps.txt"),
            state_spec("entering-game-loading", 60, 70, "entering_game_loading_steps.txt"),
            state_spec("game", 80, 90, "game_steps.txt"),
            state_spec("targeted", 100, 110, "targeted_steps.txt"),
        ]

    def test_requires_stability_before_activation(self):
        guard = LightStateGuard(self.states, stable_ms=500, hysteresis=10)
        self.assertIsNone(guard.update(50, 0))
        self.assertIsNone(guard.update(50, 400))
        self.assertEqual("dark", guard.update(50, 500))

    def test_hysteresis_prevents_jitter_switch(self):
        guard = LightStateGuard(self.states, stable_ms=0, hysteresis=20)
        self.assertEqual("dark", guard.update(50, 0))
        self.assertEqual("dark", guard.update(115, 100))
        self.assertEqual("dark", guard.update(95, 200))

    def test_switch_requires_new_state_stability(self):
        guard = LightStateGuard(self.states, stable_ms=300, hysteresis=10)
        self.assertIsNone(guard.update(50, 0))
        self.assertEqual("dark", guard.update(50, 300))
        self.assertEqual("dark", guard.update(220, 600))
        self.assertEqual("dark", guard.update(220, 899))
        self.assertEqual("bright", guard.update(220, 900))

    def test_ambiguous_overlap_is_unsafe(self):
        states = [state_spec("a", 0, 200, "a"), state_spec("b", 100, 300, "b")]
        guard = LightStateGuard(states, stable_ms=0)
        self.assertIsNone(guard.update(150, 0))

    def test_sensor_timeout_never_guesses(self):
        guard = LightStateGuard(self.states, stable_ms=0, sensor_timeout_ms=250)
        self.assertEqual("dark", guard.update(50, 0))
        self.assertEqual("dark", guard.update(None, 200))
        self.assertIsNone(guard.update(None, 251))

    def test_canonical_guard_enforces_ordered_stages(self):
        self.setUpCanonical()
        guard = LightStateGuard(self.canonical, stable_ms=0)
        for lux, profile in zip((5, 25, 45, 65, 85), (
            "desktop", "login-or-dc", "character-dashboard",
            "entering-game-loading", "game")):
            self.assertEqual(profile, guard.update(lux, lux))
            self.assertTrue(guard.last_decision["execute"])

    def test_canonical_guard_rejects_out_of_order_route(self):
        self.setUpCanonical()
        guard = LightStateGuard(self.canonical, stable_ms=0)
        self.assertEqual("desktop", guard.update(5, 0))
        self.assertIsNone(guard.update(85, 100))
        self.assertFalse(guard.last_decision["execute"])

    def test_canonical_guard_dc_fallback_and_targeted_return(self):
        self.setUpCanonical()
        guard = LightStateGuard(self.canonical, stable_ms=0)
        for lux in (5, 25, 45, 65, 85):
            self.assertIsNotNone(guard.update(lux, lux))
        self.assertEqual("targeted", guard.update(105, 105))
        self.assertEqual("targeted", guard.last_decision["context"])
        self.assertEqual("login-or-dc", guard.update(25, 125))
        self.assertEqual("dc", guard.last_decision["context"])
        self.assertEqual(2, guard.last_decision["stage"])
        # DC falls back to stage 2; the next fresh stable profiles must progress
        # through stages 2, 3, and 4 before Game can be accepted again.
        for lux, profile in ((25, "login-or-dc"), (45, "character-dashboard"),
                             (65, "entering-game-loading")):
            self.assertEqual(profile, guard.update(lux, 125 + lux))
            self.assertTrue(guard.last_decision["execute"])
        self.assertEqual("game", guard.update(85, 210))
        self.assertEqual("return-from-targeted", guard.last_decision["context"])

    def _bundle(self, include_resumable=True):
        root = tempfile.TemporaryDirectory()
        manifest_routes = dict(ROUTE_FILES)
        manifest = {
            "format": 1,
            "runtime": "combined-pico-guard-executor",
            "calibrationRevision": "guard-test-rev",
            "routes": manifest_routes,
            "profiles": [
                {"id": pid, "center": index * 100.0, "tolerance": 5.0, "stableMs": 750}
                for index, pid in enumerate((
                    "desktop", "login-or-dc", "character-dashboard",
                    "entering-game-loading", "game", "targeted"))
            ],
        }
        calibration = {
            "format": 1,
            "revision": "guard-test-rev",
            "profiles": {
                item["id"]: {"center": item["center"], "tolerance": item["tolerance"], "stable_ms": item["stableMs"]}
                for item in manifest["profiles"]
            },
        }
        Path(root.name, "guard-transition.json").write_text(json.dumps(manifest), encoding="utf-8")
        Path(root.name, "guard-calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
        for route in manifest_routes.values():
            if include_resumable or route != "resumable_steps.txt":
                Path(root.name, route).write_text("PLAN|2\n", encoding="utf-8")
        return root, manifest, calibration

    def test_valid_bundle_loads_and_keeps_metadata(self):
        root, _, _ = self._bundle()
        try:
            bundle = load_guard_bundle(root.name)
            self.assertEqual("guard-test-rev", bundle["revision"])
            self.assertEqual(6, len(bundle["states"]))
            guard = LightStateGuard.from_bundle(root.name)
            self.assertEqual("guard-test-rev", guard.bundle["revision"])
            self.assertIsNotNone(guard.transition)
        finally:
            root.cleanup()

    def test_bundle_rejects_missing_route_and_resumable(self):
        root, _, _ = self._bundle(include_resumable=False)
        try:
            with self.assertRaises(GuardBundleError):
                load_guard_bundle(root.name)
        finally:
            root.cleanup()

    def test_bundle_rejects_revision_mismatch(self):
        root, manifest, calibration = self._bundle()
        try:
            calibration["revision"] = "other-revision"
            Path(root.name, "guard-calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
            with self.assertRaisesRegex(GuardBundleError, "revision mismatch"):
                load_guard_bundle(root.name)
        finally:
            root.cleanup()

    def test_bundle_rejects_profile_mismatch(self):
        root, manifest, calibration = self._bundle()
        try:
            calibration["profiles"]["game"]["tolerance"] = 6.0
            Path(root.name, "guard-calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
            with self.assertRaisesRegex(GuardBundleError, "profile mismatch"):
                load_guard_bundle(root.name)
        finally:
            root.cleanup()

    def test_bundle_rejects_incomplete_route_map(self):
        root, manifest, _ = self._bundle()
        try:
            manifest["routes"].pop("Resumable")
            Path(root.name, "guard-transition.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(GuardBundleError, "route map"):
                load_guard_bundle(root.name)
        finally:
            root.cleanup()


if __name__ == "__main__":
    unittest.main()
