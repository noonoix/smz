import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "CIRCUITPY"))
from guard_transition import GuardTransition


class GuardTransitionTests(unittest.TestCase):
    def setUp(self):
        self.guard = GuardTransition()

    def advance_to_game(self):
        for profile in (
            "desktop",
            "login-or-dc",
            "character-dashboard",
            "entering-game-loading",
            "game",
        ):
            decision = self.guard.observe(profile)
            self.assertTrue(decision["execute"], profile)

    def test_ordered_stages_one_to_five(self):
        self.assertEqual(1, self.guard.observe("desktop")["stage"])
        self.assertEqual(2, self.guard.observe("login-or-dc")["stage"])
        self.assertEqual(3, self.guard.observe("character-dashboard")["stage"])
        self.assertEqual(4, self.guard.observe("entering-game-loading")["stage"])
        self.assertEqual(5, self.guard.observe("game")["stage"])

    def test_out_of_order_state_fails_closed(self):
        self.assertTrue(self.guard.observe("desktop")["execute"])
        decision = self.guard.observe("game")
        self.assertFalse(decision["execute"])
        self.assertEqual("game-not-expected", decision["reason"])

    def test_duplicate_stable_state_is_one_shot(self):
        self.assertTrue(self.guard.observe("desktop")["execute"])
        decision = self.guard.observe("desktop")
        self.assertFalse(decision["execute"])
        self.assertEqual("duplicate-stable-state", decision["reason"])

    def test_unknown_rearms_after_state_change(self):
        self.assertTrue(self.guard.observe("desktop")["execute"])
        self.guard.observe_unknown()
        decision = self.guard.observe("desktop")
        self.assertFalse(decision["execute"])
        self.assertEqual("desktop-only-valid-at-start", decision["reason"])

    def test_dc_falls_back_to_stage_two(self):
        self.advance_to_game()
        decision = self.guard.observe("login-or-dc")
        self.assertTrue(decision["execute"])
        self.assertEqual("dc", decision["context"])
        self.assertEqual(2, decision["stage"])
        self.assertEqual("login_or_dc_steps.txt", decision["route"])

    def test_targeted_is_side_state_and_returns_to_game(self):
        self.advance_to_game()
        targeted = self.guard.observe("targeted")
        self.assertTrue(targeted["execute"])
        self.assertEqual("targeted", targeted["context"])
        returned = self.guard.observe("game")
        self.assertFalse(returned["execute"])
        self.assertEqual("return-from-targeted", returned["context"])
        self.assertEqual(5, returned["stage"])

    def test_dc_has_priority_over_targeted(self):
        self.advance_to_game()
        self.assertTrue(self.guard.observe("targeted")["execute"])
        dc = self.guard.observe("login-or-dc")
        self.assertTrue(dc["execute"])
        self.assertEqual("dc", dc["context"])
        self.assertEqual(2, dc["stage"])

    def test_unknown_profile_never_selects_a_route(self):
        decision = self.guard.observe("not-a-profile")
        self.assertFalse(decision["execute"])
        self.assertIsNone(decision["route"])


if __name__ == "__main__":
    unittest.main()
