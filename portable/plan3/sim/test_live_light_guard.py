import unittest

from live_light_guard import LightStateGuard, state_spec


class LiveLightGuardTests(unittest.TestCase):
    def setUp(self):
        self.states = [
            state_spec("dark", 0, 100, "dark.plan.txt"),
            state_spec("bright", 160, 400, "bright.plan.txt"),
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


if __name__ == "__main__":
    unittest.main()
