import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CIRCUITPY"))
from live_light_guard import LightStateGuard, state_spec


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
        self.assertEqual("game", guard.update(85, 185))
        self.assertEqual("return-from-targeted", guard.last_decision["context"])


if __name__ == "__main__":
    unittest.main()
