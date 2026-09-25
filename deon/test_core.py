"""Regression tests for the obligation semantics of the automaton and the calibration edge cases."""
import math
import unittest

import numpy as np

from core import Action, DeonticPolicyAutomaton, Policy, calibrate_threshold


class ObligationSemanticsTests(unittest.TestCase):
    def test_self_trigger_requires_later_occurrence(self):
        dpa = DeonticPolicyAutomaton(Policy(obligations={"tick": "tick"}))
        ok, _, state = dpa.step(dpa.start(), Action("tick"))
        self.assertTrue(ok)
        self.assertEqual(state.pending, {"tick"})
        self.assertFalse(dpa.finalize(state)[0])

    def test_termination_reports_pending_obligation(self):
        dpa = DeonticPolicyAutomaton(Policy(obligations={"charge": "receipt"}))
        ok, _, state = dpa.step(dpa.start(), Action("charge"))
        self.assertTrue(ok)
        compliant, reason = dpa.finalize(state)
        self.assertFalse(compliant)
        self.assertIn("receipt", reason)

    def test_repeated_boolean_triggers_coalesce(self):
        dpa = DeonticPolicyAutomaton(Policy(obligations={"charge": "receipt"}))
        state = dpa.start()
        for _ in range(2):
            _, _, state = dpa.step(state, Action("charge"))
        self.assertEqual(state.pending, {"receipt"})
        _, _, state = dpa.step(state, Action("receipt"))
        self.assertTrue(dpa.finalize(state)[0])

    def test_refusal_is_atomic_and_leaves_state_unchanged(self):
        dpa = DeonticPolicyAutomaton(Policy(prohibited_actions={"deny"}))
        state = dpa.start()
        ok, _, next_state = dpa.step(state, Action("deny"))
        self.assertFalse(ok)
        self.assertIs(next_state, state)

    def test_serialized_check_execute_update_observes_committed_quota(self):
        dpa = DeonticPolicyAutomaton(Policy(quota={"api": 1}))
        first_ok, _, committed = dpa.step(dpa.start(), Action("call", resource="api"))
        second_ok, reason, after_second = dpa.step(
            committed, Action("call", resource="api")
        )
        self.assertTrue(first_ok)
        self.assertFalse(second_ok)
        self.assertIn("quota exceeded", reason)
        self.assertIs(after_second, committed)


class CalibrationEdgeCaseTests(unittest.TestCase):
    def test_empty_violation_pool_abstains_all(self):
        tau = calibrate_threshold(np.array([0.1]), np.array([0]), 0.1)
        self.assertEqual(tau, -math.inf)

    def test_rank_zero_is_negative_infinity(self):
        tau = calibrate_threshold(np.array([0.8]), np.array([1]), 0.1)
        self.assertEqual(tau, -math.inf)


if __name__ == "__main__":
    unittest.main()
