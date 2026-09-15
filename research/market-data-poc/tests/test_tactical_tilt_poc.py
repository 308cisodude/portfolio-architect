import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import tactical_tilt_poc as tt


WORLD = "IE00BJ0KDQ92"
ROBOTICS = "IE00BYZK4552"
CYBER = "IE00BLPK3577"


def target(isin, pct, value, *, buy=True, eligible=True, name=None):
    return {
        "isin": isin,
        "name": name or isin,
        "target_pct": pct,
        "current_value_eur": value,
        "buy_enabled": buy,
        "planner_eligible": eligible,
    }


def context_item(isin, *, as_of="2026-09-14", r5=-0.01, r20=-0.02, dd=-0.03):
    return {
        "isin": isin,
        "name": isin,
        "status": "ok",
        "symbol": "TEST.DEX",
        "currency": "EUR",
        "region": "XETRA",
        "metrics": {
            "as_of": as_of,
            "latest_close": 100.0,
            "return_5d": r5,
            "return_20d": r20,
            "drawdown_from_20d_high": dd,
        },
    }


class SignalTests(unittest.TestCase):
    def test_strong_rebound_suppresses_prior_weakness(self):
        s = tt.tactical_signals(
            {"return_5d": 0.0818, "return_20d": -0.08, "drawdown_from_20d_high": -0.08}
        )
        self.assertEqual(s["rebound_penalty"], 1.0)
        self.assertEqual(s["rebound_aware"], 0.0)

    def test_real_robotics_fixture_scores_above_world(self):
        world = tt.tactical_signals(
            {"return_5d": -0.0071, "return_20d": -0.0172, "drawdown_from_20d_high": -0.0139}
        )
        robot = tt.tactical_signals(
            {"return_5d": -0.0301, "return_20d": -0.0729, "drawdown_from_20d_high": -0.0517}
        )
        self.assertGreater(robot["rebound_aware"], world["rebound_aware"])

    def test_positive_drawdown_value_cannot_create_positive_signal(self):
        s = tt.tactical_signals(
            {"return_5d": 0.0, "return_20d": 0.0, "drawdown_from_20d_high": 0.01}
        )
        self.assertEqual(s["drawdown_only"], 0.0)


class AllocationTests(unittest.TestCase):
    def test_post_contribution_deficit_math(self):
        targets = [
            tt.AllocationTarget("AAAAAAAAAAAA", "A", 50.0, 450.0, True, True),
            tt.AllocationTarget("BBBBBBBBBBBB", "B", 50.0, 550.0, True, True),
        ]
        current, post, candidates, _ = tt.build_candidates(100.0, targets)
        self.assertEqual(current, 1000.0)
        self.assertEqual(post, 1100.0)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].target.isin, "AAAAAAAAAAAA")
        self.assertAlmostEqual(candidates[0].deficit_eur, 100.0)

    def test_disabled_target_is_not_candidate(self):
        targets = [
            tt.AllocationTarget("AAAAAAAAAAAA", "A", 60.0, 400.0, False, True),
            tt.AllocationTarget("BBBBBBBBBBBB", "B", 40.0, 600.0, True, True),
        ]
        with self.assertRaises(tt.TiltError):
            tt.build_candidates(100.0, targets)


class MarketContextGateTests(unittest.TestCase):
    def candidates(self):
        return [
            tt.Candidate(tt.AllocationTarget(WORLD, "World", 50, 500, True, True), 50, 600, 100),
            tt.Candidate(tt.AllocationTarget(ROBOTICS, "Robotics", 50, 510, True, True), 50, 600, 90),
        ]

    def test_weekend_calendar_age_three_is_accepted(self):
        ctx = {"targets": [context_item(WORLD, as_of="2026-09-11"), context_item(ROBOTICS, as_of="2026-09-11")]}
        active, _, as_of, _ = tt.evaluate_market_context(
            ctx, self.candidates(), evaluation_date=date(2026, 9, 14), max_age_days=4
        )
        self.assertTrue(active)
        self.assertEqual(as_of, "2026-09-11")

    def test_stale_context_neutralizes_tactical_layer(self):
        ctx = {"targets": [context_item(WORLD, as_of="2026-09-08"), context_item(ROBOTICS, as_of="2026-09-08")]}
        active, reason, _, _ = tt.evaluate_market_context(
            ctx, self.candidates(), evaluation_date=date(2026, 9, 14), max_age_days=4
        )
        self.assertFalse(active)
        self.assertIn("stale", reason)

    def test_missing_candidate_context_neutralizes_globally(self):
        ctx = {"targets": [context_item(WORLD)]}
        active, reason, _, _ = tt.evaluate_market_context(
            ctx, self.candidates(), evaluation_date=date(2026, 9, 15), max_age_days=4
        )
        self.assertFalse(active)
        self.assertIn("missing", reason)

    def test_mixed_as_of_neutralizes_globally(self):
        ctx = {"targets": [context_item(WORLD, as_of="2026-09-14"), context_item(ROBOTICS, as_of="2026-09-13")]}
        active, reason, _, _ = tt.evaluate_market_context(
            ctx, self.candidates(), evaluation_date=date(2026, 9, 15), max_age_days=4
        )
        self.assertFalse(active)
        self.assertEqual(reason, "market_context_mixed_as_of")


class ModelTests(unittest.TestCase):
    def rows(self, world_deficit=100.0, robotics_deficit=90.0):
        candidates = [
            tt.Candidate(tt.AllocationTarget(WORLD, "World", 45, 1000, True, True), 45, 1100, world_deficit),
            tt.Candidate(tt.AllocationTarget(ROBOTICS, "Robotics", 5, 100, True, True), 5, 190, robotics_deficit),
        ]
        market = {
            WORLD: {"signals": {"drawdown_only": 0.0, "multi_window": 0.0, "rebound_aware": 0.0}},
            ROBOTICS: {"signals": {"drawdown_only": 1.0, "multi_window": 1.0, "rebound_aware": 1.0}},
        }
        return candidates, market

    def test_bounded_model_can_change_close_decision(self):
        candidates, market = self.rows(world_deficit=100.0, robotics_deficit=90.0)
        _, policy = tt.calculate_models(
            candidates, market, tactical_active=True, contribution_eur=350.0, tilt_budget_pct=10.0, tie_band_pct=10.0
        )
        self.assertEqual(policy["models"]["bounded_rebound_aware"]["selected_isin"], ROBOTICS)
        self.assertAlmostEqual(policy["models"]["bounded_rebound_aware"]["strategic_sacrifice_eur"], 10.0)

    def test_bounded_model_cannot_overcome_gap_larger_than_budget(self):
        candidates, market = self.rows(world_deficit=100.0, robotics_deficit=60.0)
        _, policy = tt.calculate_models(
            candidates, market, tactical_active=True, contribution_eur=350.0, tilt_budget_pct=10.0, tie_band_pct=10.0
        )
        self.assertEqual(policy["models"]["bounded_rebound_aware"]["selected_isin"], WORLD)

    def test_tie_break_cannot_leave_strategic_band(self):
        candidates, market = self.rows(world_deficit=100.0, robotics_deficit=60.0)
        _, policy = tt.calculate_models(
            candidates, market, tactical_active=True, contribution_eur=350.0, tilt_budget_pct=10.0, tie_band_pct=10.0
        )
        self.assertEqual(policy["models"]["tie_break_rebound_aware"]["selected_isin"], WORLD)

    def test_neutral_tactical_context_preserves_baseline_for_all_models(self):
        candidates, market = self.rows(world_deficit=100.0, robotics_deficit=90.0)
        _, policy = tt.calculate_models(
            candidates, market, tactical_active=False, contribution_eur=350.0, tilt_budget_pct=10.0, tie_band_pct=10.0
        )
        for result in policy["models"].values():
            self.assertEqual(result["selected_isin"], WORLD)


class EndToEndFixtureTests(unittest.TestCase):
    def test_supplied_fixture_demonstrates_rebound_safe_tilt(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            doc = tt.evaluate(
                root / "examples" / "allocation_state.example.json",
                root / "examples" / "market_context_2026-09-14.json",
                Path(tmp),
                evaluation_date=date(2026, 9, 15),
                tilt_budget_pct=10.0,
                tie_band_pct=10.0,
                max_market_age_days=4,
            )
        models = doc["policy"]["models"]
        self.assertEqual(models["baseline"]["selected_isin"], WORLD)
        self.assertEqual(models["bounded_rebound_aware"]["selected_isin"], ROBOTICS)
        self.assertEqual(models["tie_break_rebound_aware"]["selected_isin"], ROBOTICS)
        cyber = next(row for row in doc["candidate_scores"] if row["isin"] == CYBER)
        self.assertEqual(cyber["market_context"]["signals"]["rebound_aware"], 0.0)
        self.assertLessEqual(models["bounded_rebound_aware"]["strategic_sacrifice_eur"], doc["policy"]["tilt_budget_eur"])


if __name__ == "__main__":
    unittest.main()
